"""Coupled 0D cylinder / 1D duct system for a single-cylinder four-stroke engine.

Time integration: SSPRK2 (Heun) over the joint state (all duct cells and all
finite 0D volumes) with one global step, admissibility retries (step halving)
and exact landing on crank-angle events (TDC/BDC, valve events, SOC/EOC,
cycle boundaries).  Every exchanged quantity is accumulated with the same RK
weights as the state, so the conservation ledgers close to roundoff.

The topology is a list of ``Connection`` objects binding a duct end to a 0D
volume (cylinder or fixed reservoir) through a restriction law, so new
components (plenums, throttles, multi-cylinder manifolds) reuse the same
boundary and ledger machinery.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time

import numpy as np

from .closures import WoschniHeatTransfer
from .combustion import Wiebe, products_change
from .duct import Duct, InadmissibleState
from .kinematics import SliderCrank
from .restriction import EndCell, RestrictionError, VolumeGas, restriction_flux
from .thermo import Mixture, ThermoError
from .twozone import TwoZoneModel
from .valves import CYCLE_DEG, Valve, wrap

RECOVERABLE = (InadmissibleState, RestrictionError, ThermoError, ValueError, OverflowError,
               ZeroDivisionError, FloatingPointError)


class Reservoir:
    """Infinite 0D volume with fixed quiescent state (ambient, test benches)."""
    finite = False

    def __init__(self, name: str, mixture: Mixture, p: float, T: float, Y, xb: float = 0.0):
        self.name = name
        self.gas = VolumeGas.from_mixture(mixture, p, T, Y, xb)


class Plenum:
    """Finite adiabatic 0D volume of fixed size (airbox, surge tank, test vessel).

    State: species masses, tracer mass, internal energy -- exactly the cylinder layout."""
    finite = True

    def __init__(self, name: str, mixture: Mixture, volume_m3: float):
        if not (math.isfinite(volume_m3) and volume_m3 > 0):
            raise ValueError("plenum volume must be positive")
        self.name, self.mix, self.volume = name, mixture, volume_m3
        self._t_guess = 300.0

    def state(self, p, T, Y, xb=0.0):
        Y = np.asarray(Y, dtype=float)
        m = p * self.volume / (float(self.mix.gas_constant(Y)) * T)
        z = np.empty(self.mix.ns + 2)
        z[:self.mix.ns] = m * Y
        z[self.mix.ns] = m * xb
        z[self.mix.ns + 1] = m * float(self.mix.internal_energy(Y, T))
        return z

    def gas(self, z):
        ns = self.mix.ns
        m = z[:ns].sum()
        if not (m > 0 and np.all(z[:ns] >= -1e-12 * m)):
            raise InadmissibleState(f"{self.name}: negative plenum mass/species")
        Y = z[:ns] / m
        T = self.mix.temperature_from_energy(Y, z[ns + 1] / m, self._t_guess)
        self._t_guess = T
        R = float(self.mix.gas_constant(Y))
        return VolumeGas(m * R * T / self.volume, T, Y, z[ns] / m, float(z[ns + 1] / m + R * T), R,
                         float(self.mix.cp(Y, T))), m


@dataclass(frozen=True)
class CombustionSpec:
    fuel: str
    wiebe: Wiebe
    efficiency: float = 0.98
    water_gas_k: float = 3.5
    model: str = "single_zone"   # "single_zone" (complete combustion products) | "two_zone_equilibrium"

    def __post_init__(self):
        if not 0.0 <= self.efficiency <= 1.0:
            raise ValueError("combustion efficiency must lie in [0, 1]")
        if self.model not in ("single_zone", "two_zone_equilibrium"):
            raise ValueError("combustion model must be single_zone or two_zone_equilibrium")


class Cylinder:
    """Single-zone, spatially uniform cylinder (finite 0D volume with piston)."""
    finite = True

    def __init__(self, name: str, mixture: Mixture, geometry: SliderCrank, *,
                 heat_transfer: WoschniHeatTransfer | None = None,
                 combustion: CombustionSpec | None = None,
                 intake_valves: Valve | None = None, exhaust_valves: Valve | None = None):
        self.name, self.mix, self.geometry = name, mixture, geometry
        self.heat_transfer, self.combustion = heat_transfer, combustion
        self.intake, self.exhaust = intake_valves, exhaust_valves
        self._t_guess = 1000.0
        self.woschni_reference = None  # (p, T, V, gamma) at IVC
        self.burn = None               # (fuel burned per unit x_b: species vector, unburned mass)
        self.zones = (TwoZoneModel(mixture, geometry)
                      if combustion is not None and combustion.model == "two_zone_equilibrium" else None)

    def state(self, p, T, Y, xb, theta):
        Y = np.asarray(Y, dtype=float)
        V = self.geometry.volume(theta)
        m = p * V / (float(self.mix.gas_constant(Y)) * T)
        z = np.empty(self.mix.ns + 2)
        z[:self.mix.ns] = m * Y
        z[self.mix.ns] = m * xb
        z[self.mix.ns + 1] = m * float(self.mix.internal_energy(Y, T))
        return z

    def totals(self, z, theta):
        """Conserved totals (species, tracer, U) whatever the state layout."""
        return self.zones.totals(z, theta) if z.size == 2 else z

    def gas(self, z, theta):
        if z.size == 2:
            return self.zones.gas_view(z, theta)
        ns = self.mix.ns
        mi = z[:ns]
        m = mi.sum()
        if not (m > 0 and np.all(mi >= -1e-12 * m)):
            raise InadmissibleState(f"{self.name}: negative cylinder mass/species")
        Y = mi / m
        T = self.mix.temperature_from_energy(Y, z[ns + 1] / m, self._t_guess)
        self._t_guess = T
        V = self.geometry.volume(theta)
        R = float(self.mix.gas_constant(Y))
        p = m * R * T / V
        return VolumeGas(p, T, Y, z[ns] / m, float(z[ns + 1] / m + R * T), R,
                         float(self.mix.cp(Y, T))), m, V

    def gas_exchange(self, theta):
        return any(v is not None and v.is_open(theta) for v in (self.intake, self.exhaust))

    def combustion_phase(self, theta):
        """SOC .. EVO window (Woschni C2 term)."""
        if self.combustion is None or self.exhaust is None:
            return False
        soc = self.combustion.wiebe.start_deg
        return (theta - soc) % CYCLE_DEG < (self.exhaust.lift_law.open_deg - soc) % CYCLE_DEG


class Connection:
    """Duct end <-> 0D volume through a restriction.

    ``area(theta)`` returns (A_volume_to_duct, A_duct_to_volume) in m^2."""

    def __init__(self, name, duct: Duct, side: str, volume, area):
        if side not in ("left", "right"):
            raise ValueError("side must be left or right")
        self.name, self.duct, self.side, self.volume, self.area = name, duct, side, volume, area
        self.pipe_area = float(duct.area[0] if side == "left" else duct.area[-1])

    @classmethod
    def valve(cls, name, duct, side, cylinder, valve: Valve, role: str):
        if role not in ("intake", "exhaust"):
            raise ValueError("role must be intake or exhaust")
        into_duct, out_of_duct = ("reverse", "forward") if role == "intake" else ("forward", "reverse")
        conn = cls(name, duct, side, cylinder,
                   lambda th: (valve.effective_area(th, into_duct), valve.effective_area(th, out_of_duct)))
        conn.valve_law = valve
        limit = valve.max_effective_area()
        if limit > conn.pipe_area:
            raise ValueError(f"{name}: maximum effective valve area {limit:.4e} m2 exceeds "
                             f"the port duct area {conn.pipe_area:.4e} m2")
        return conn

    @classmethod
    def open_end(cls, name, duct, side, reservoir, cd_inflow=1.0, cd_outflow=1.0):
        """Pipe end to a reservoir; inflow = reservoir -> duct."""
        A = float(duct.area[0] if side == "left" else duct.area[-1])
        return cls(name, duct, side, reservoir, lambda th: (cd_inflow * A, cd_outflow * A))


@dataclass
class Ledger:
    """Integrated exchanges (RK-weighted).  Units: kg, J."""
    ns: int
    reservoir_in: np.ndarray = None      # species (ns), tracer, energy entering the system
    piston_work: float = 0.0             # integral of p dV (work done by gas)
    cylinder_heat_loss: float = 0.0
    duct_heat_gain: float = 0.0
    tracer_source: float = 0.0

    def __post_init__(self):
        if self.reservoir_in is None:
            self.reservoir_in = np.zeros(self.ns + 2)


@dataclass
class CycleRecord:
    index: int
    theta_start: float
    work_net: float = 0.0
    work_by_stroke: dict = field(default_factory=dict)
    connection_mass: dict = field(default_factory=dict)     # name -> [into volume gross, out of volume gross]
    connection_species: dict = field(default_factory=dict)  # name -> species/tracer/energy into volume
    heat_loss: float = 0.0
    duct_heat_gain: float = 0.0
    fuel_burned: float = 0.0
    p_max: float = 0.0
    theta_p_max: float = float("nan")
    T_max: float = 0.0
    T_b_max: float = 0.0
    T_u_max: float = float("nan")   # only defined while an unburned zone exists (two-zone model)
    snapshots: dict = field(default_factory=dict)
    start_inventory: dict = field(default_factory=dict)
    end_inventory: dict = field(default_factory=dict)
    trace: dict = field(default_factory=dict)
    steps: int = 0
    rejected_steps: int = 0
    choked_steps: dict = field(default_factory=dict)


STROKES = (("intake", -360.0, -180.0), ("compression", -180.0, 0.0),
           ("expansion", 0.0, 180.0), ("exhaust", 180.0, 360.0))


class FourStrokeEngine:
    def __init__(self, mixture: Mixture, cylinder: Cylinder, ducts: dict, connections: list, rpm: float,
                 *, cfl: float = 0.8, max_dtheta: float = 0.5, theta_start: float = -360.0,
                 sensors: dict | None = None, plenums: dict | None = None,
                 restriction_model: str = "V2"):
        if restriction_model not in ("V1", "V2"):
            raise ValueError("restriction_model must be V1 or V2")
        self.plenums = plenums or {}
        self.restriction_stagnation = restriction_model == "V2"
        if not (rpm > 0 and 0 < cfl <= 0.9 and max_dtheta > 0):
            raise ValueError("invalid rpm / CFL / max_dtheta")
        self.mix, self.cylinder, self.ducts, self.connections = mixture, cylinder, ducts, connections
        self.rpm, self.cfl, self.max_dtheta = rpm, cfl, max_dtheta
        self.deg_per_s = 6.0 * rpm
        self.theta_start = theta_start
        self.ns = mixture.ns
        self.sensors = sensors or {}
        events = {-360.0, -180.0, 0.0, 180.0, wrap(theta_start)}
        for v in (cylinder.intake, cylinder.exhaust):
            if v is not None:
                events.update(wrap(e) for e in v.lift_law.events())
        if cylinder.combustion is not None:
            w = cylinder.combustion.wiebe
            events.update((wrap(w.start_deg), wrap(w.start_deg + w.duration_deg)))
            self._check_closed_during_burn()
        self.events = sorted(events)

    def _check_closed_during_burn(self):
        w = self.cylinder.combustion.wiebe
        for th in np.linspace(w.start_deg, w.start_deg + w.duration_deg, 721):
            if self.cylinder.gas_exchange(wrap(th)):
                raise ValueError("a valve is open during combustion; single-zone burn model requires a closed cylinder")

    # ----------------------------------------------------------------- state
    def initial_state(self, *, cylinder: dict, ducts: dict, plenums: dict | None = None):
        q = {name: d.uniform(**ducts[name]) for name, d in self.ducts.items()}
        z = self.cylinder.state(theta=wrap(self.theta_start), **cylinder)
        plenums = plenums or {}
        if set(plenums) != set(self.plenums):
            raise ValueError("initial plenum states must match the plenums of the engine")
        return {"ducts": q, "cyl": z, "plen": {k: self.plenums[k].state(**plenums[k]) for k in self.plenums}}

    @staticmethod
    def _axpy(state, deriv, dt):
        return {"ducts": {k: v + dt * deriv["ducts"][k] for k, v in state["ducts"].items()},
                "cyl": state["cyl"] + dt * deriv["cyl"],
                "plen": {k: v + dt * deriv["plen"][k] for k, v in state["plen"].items()}}

    @staticmethod
    def _average(a, b):
        return {"ducts": {k: 0.5 * (v + b["ducts"][k]) for k, v in a["ducts"].items()},
                "cyl": 0.5 * (a["cyl"] + b["cyl"]),
                "plen": {k: 0.5 * (v + b["plen"][k]) for k, v in a["plen"].items()}}

    def inventory(self, state):
        """System totals: species (ns), tracer, energy (momentum excluded)."""
        total = np.zeros(self.ns + 2)
        for name, d in self.ducts.items():
            inv = d.inventory(state["ducts"][name])
            total[:self.ns + 1] += inv[:self.ns + 1]
            total[self.ns + 1] += inv[self.ns + 2]
        total += self.cylinder.totals(state["cyl"], getattr(self, "_theta_now", self.theta_start))
        for z in state["plen"].values():
            total += z
        return total

    # ------------------------------------------------------------------- RHS
    def rhs(self, state, theta_abs):
        theta = wrap(theta_abs)
        self._theta_now = theta
        ns, nv = self.ns, self.ns + 3
        prim = {name: d.primitive(state["ducts"][name]) for name, d in self.ducts.items()}
        cgas, cmass, cvol = self.cylinder.gas(state["cyl"], theta)
        two_zone = state["cyl"].size == 2
        pgas = {k: pl.gas(state["plen"][k]) for k, pl in self.plenums.items()}
        faces, speeds, fallbacks = {}, {}, 0
        for name, d in self.ducts.items():
            F = np.empty((d.n + 1, nv))
            s = np.empty(d.n + 1)
            Fi, si, nf = d.interior_flux(prim[name])
            F[1:-1], s[1:-1] = Fi, si
            fallbacks += nf
            faces[name], speeds[name] = F, s
        dz = np.zeros(2 if two_zone else ns + 2)
        dplen = {k: np.zeros(ns + 2) for k in self.plenums}
        res_in = np.zeros(ns + 2)
        exchange = {}
        for c in self.connections:
            w = prim[c.duct.name]
            index = 0 if c.side == "left" else -1
            a_into, a_out = c.area(theta)
            is_plenum = isinstance(c.volume, Plenum)
            vol_gas = (cgas if c.volume is self.cylinder else pgas[c.volume.name][0] if is_plenum
                       else c.volume.gas)
            r = restriction_flux(EndCell.from_primitive(w, index), c.side, c.pipe_area, a_into, a_out,
                                 vol_gas, ns, stagnation=self.restriction_stagnation)
            faces[c.duct.name][index] = r.flux_x
            speeds[c.duct.name][index] = abs(w["u"][index]) + w["a"][index]
            if c.volume is self.cylinder:
                if two_zone:
                    if a_into > 0.0 or a_out > 0.0:
                        raise InadmissibleState("valve open while the cylinder is in the two-zone state")
                else:
                    dz += r.to_volume
            elif is_plenum:
                dplen[c.volume.name] += r.to_volume
            else:
                res_in -= r.to_volume
            exchange[c.name] = r
        dq, dt_limit, duct_heat = {}, math.inf, 0.0
        for name, d in self.ducts.items():
            S, heat = d.sources(prim[name])
            duct_heat += heat
            F = faces[name]
            dq[name] = (F[:-1] - F[1:] + S) / d.volume[:, None]
            dt_limit = min(dt_limit, d.time_step_limit(prim[name], speeds[name]))
        geo = self.cylinder.geometry
        dVdt = geo.dvolume_dt(theta, self.rpm)
        piston_power = cgas.p * dVdt
        q_loss, h_coef, q_u = 0.0, 0.0, 0.0
        ht = self.cylinder.heat_transfer
        if ht is not None:
            h_coef = ht.coefficient(bore_m=geo.bore_m, p_pa=cgas.p, T_K=cgas.T,
                                    mean_piston_speed=geo.mean_piston_speed(self.rpm),
                                    displacement=geo.displacement,
                                    gas_exchange=self.cylinder.gas_exchange(theta),
                                    combustion_phase=self.cylinder.combustion_phase(theta),
                                    reference=self.cylinder.woschni_reference, volume=cvol)
            if two_zone:
                zs = self.cylinder.zones.last
                fu, fb = zs.V_u / cvol, zs.V_b / cvol
                a_liner = geo.liner_area(theta)
                q_u = ht.heat_loss_rate(h_coef, zs.T_u, geo.piston_area * fu, a_liner * fu) if zs.m_u > 0.0 else 0.0
                q_loss = q_u + ht.heat_loss_rate(h_coef, zs.T_b, geo.piston_area * fb, a_liner * fb)
            else:
                q_loss = ht.heat_loss_rate(h_coef, cgas.T, geo.piston_area, geo.liner_area(theta))
        if two_zone:
            zs = self.cylinder.zones.last
            dz[0] = -(piston_power + q_loss)
            # the unburned zone only loses its own share of the wall heat: ds_u = -q_u dt / (m_u T_u)
            dz[1] = -q_u / (zs.m_u * zs.T_u) if (ht is not None and zs.m_u > 1e-9 * self.cylinder.zones.ctx.m) else 0.0
        else:
            dz[ns + 1] -= piston_power + q_loss
        mass_rate = sum(abs(r.mdot_into_duct) for c, r in zip(self.connections, exchange.values())
                        if c.volume is self.cylinder)
        if mass_rate > 0:
            dt_limit = min(dt_limit, 0.2 * cmass / mass_rate / self.cfl)
        for k in self.plenums:
            rate = sum(abs(r.mdot_into_duct) for c, r in zip(self.connections, exchange.values())
                       if c.volume is self.plenums[k])
            if rate > 0:
                dt_limit = min(dt_limit, 0.2 * pgas[k][1] / rate / self.cfl)
        deriv = {"ducts": dq, "cyl": dz, "plen": dplen}
        rates = dict(reservoir_in=res_in, piston_power=piston_power, heat_loss=q_loss,
                     duct_heat=duct_heat, exchange=exchange, dt_limit=dt_limit, fallbacks=fallbacks,
                     gas=cgas, mass=cmass, volume=cvol, h=h_coef, theta=theta, prim=prim,
                     plenum_gas={k: v[0] for k, v in pgas.items()},
                     zones=self.cylinder.zones.last if two_zone else None)
        return deriv, rates

    def burn_source(self, theta_a, theta_b, dt):
        """Constant source over the step reproducing the exact Wiebe increment."""
        comb = self.cylinder.combustion
        if comb is None or self.cylinder.burn is None:
            return None, 0.0
        w = comb.wiebe
        since_a = (wrap(theta_a) - w.start_deg) % CYCLE_DEG
        if since_a >= w.duration_deg:
            return None, 0.0
        dx = w.fraction(since_a + (theta_b - theta_a)) - w.fraction(since_a)
        if dx <= 0:
            return None, 0.0
        if self.cylinder.zones is not None:  # zone closure carries the composition change itself
            return None, dx
        species_per_x, unburned = self.cylinder.burn
        src = np.zeros(self.ns + 2)
        src[:self.ns] = species_per_x * dx / dt
        src[self.ns] = unburned * dx / dt
        return src, dx

    # ------------------------------------------------------------- stepping
    def validate(self, state, theta_abs):
        for name, d in self.ducts.items():
            d.primitive(state["ducts"][name])
        self.cylinder.gas(state["cyl"], wrap(theta_abs))
        for k, pl in self.plenums.items():
            pl.gas(state["plen"][k])

    def next_event(self, theta_abs):
        theta = wrap(theta_abs)
        gaps = [(e - theta) % CYCLE_DEG for e in self.events]
        gap = min(g if g > 1e-9 else CYCLE_DEG for g in gaps)
        return theta_abs + gap

    def step(self, state, theta_abs, rates0, deriv0):
        target = min(self.next_event(theta_abs), getattr(self, "_theta_stop", math.inf))
        dtheta = min(self.max_dtheta, self.cfl * rates0["dt_limit"] * self.deg_per_s, target - theta_abs)
        rejected = 0
        for _ in range(16):
            theta_b = target if abs(theta_abs + dtheta - target) <= 1e-9 else theta_abs + dtheta
            dt = (theta_b - theta_abs) / self.deg_per_s
            src, dx = self.burn_source(theta_abs, theta_b, dt)
            d0 = deriv0 if src is None else dict(deriv0, cyl=deriv0["cyl"] + src)
            try:
                with np.errstate(over="raise", divide="raise", invalid="raise", under="ignore"):
                    s1 = self._axpy(state, d0, dt)
                    d1, rates1 = self.rhs(s1, theta_b)
                    if dt > self.cfl * rates1["dt_limit"] * 1.25:
                        raise InadmissibleState("stage CFL")
                    if src is not None:
                        d1 = dict(d1, cyl=d1["cyl"] + src)
                    s2 = self._axpy(s1, d1, dt)
                    new = self._average(state, s2)
                    self.validate(new, theta_b)
                return new, theta_b, dt, rates1, dx, rejected
            except RECOVERABLE as exc:
                rejected += 1
                dtheta *= 0.5
                last = f"{type(exc).__name__}: {exc}"
        raise InadmissibleState(f"step rejected 16 times at theta={theta_abs:.6f}; last: {last}")

    # ------------------------------------------------------------------ run
    def run(self, state, cycles: int, *, wall_limit_s: float = 3600.0, on_cycle=None,
            keep_traces: str = "last", convergence=None, cancel_event=None):
        started = time.monotonic()
        theta = self.theta_start
        ledger = Ledger(self.ns)
        inventory0 = self.inventory(state)
        records, status, reason = [], "completed", "requested_cycles"
        deriv, rates = self.rhs(state, theta)
        record = self._new_record(0, theta, state, rates)
        theta_end = self.theta_start + cycles * CYCLE_DEG  # ``cycles`` may be fractional
        self._theta_stop = theta_end
        max_closure = np.zeros(3)
        while theta < theta_end - 1e-9:
            if time.monotonic() - started > wall_limit_s:
                status, reason = "incomplete", "wall_limit"
                break
            try:
                new, theta_b, dt, rates_b, dx, rejected = self.step(state, theta, rates, deriv)
            except RECOVERABLE as exc:
                status, reason = "failed_numerical", f"{type(exc).__name__}: {exc}"
                break
            self._accumulate(ledger, record, rates, rates_b, dt, theta, theta_b, dx, rejected)
            state, theta = new, theta_b
            state = self._on_event(state, theta, record)
            deriv, rates = self.rhs(state, theta)
            self._sample(record, state, theta, rates)
            closure = self.closure(ledger, inventory0, state)
            max_closure = np.maximum(max_closure, [closure["mass"], closure["energy"], closure["elements"]])
            if abs(wrap(theta) - wrap(self.theta_start)) < 1e-9 and theta > record.theta_start + 1.0:
                record.end_inventory = self._inventories(state)
                self._finish_record(record, keep_traces == "all")
                records.append(record)
                if on_cycle is not None:
                    on_cycle(record)
                if keep_traces == "last" and len(records) > 1:
                    records[-2].trace = {k: v for k, v in records[-2].trace.items() if k == "pressure_grid"}
                if convergence is not None and convergence(records):
                    reason = "periodic_converged"
                    break
                # Cancellation is observed only after a complete 720-degree cycle;
                # the physical step sequence and convergence checks are unchanged.
                if cancel_event is not None and cancel_event.is_set():
                    status, reason = "incomplete", "cancelled_by_user"
                    break
                record = self._new_record(len(records), theta, state, rates)
        return dict(status=status, reason=reason, cycles=records, state=state, theta=theta,
                    ledger=ledger, closure=self.closure(ledger, inventory0, state),
                    max_closure=dict(zip(("mass", "energy", "elements"), max_closure.tolist())),
                    wall_seconds=time.monotonic() - started, partial_cycle=record)

    def closure(self, ledger, inventory0, state):
        inv = self.inventory(state)
        ns = self.ns
        energy_balance = (inventory0[ns + 1] + ledger.reservoir_in[ns + 1] - ledger.piston_work
                          - ledger.cylinder_heat_loss + ledger.duct_heat_gain)
        mass_now, mass_expected = inv[:ns].sum(), inventory0[:ns].sum() + ledger.reservoir_in[:ns].sum()
        el_now = self.mix.element_masses(inv[:ns])
        el_expected = self.mix.element_masses(inventory0[:ns] + ledger.reservoir_in[:ns])
        energy_scale = max(abs(inventory0[ns + 1]), abs(inv[ns + 1]),
                           abs(ledger.piston_work) + abs(ledger.cylinder_heat_loss), 1.0)
        return dict(mass=abs(mass_now - mass_expected) / max(mass_now, mass_expected),
                    energy=abs(inv[ns + 1] - energy_balance) / energy_scale,
                    elements=float(np.max(np.abs(el_now - el_expected) / np.maximum(np.abs(el_expected), 1e-30),
                                          initial=0.0)),
                    tracer=abs(inv[ns] - inventory0[ns] - ledger.reservoir_in[ns] - ledger.tracer_source)
                    / max(mass_now, 1e-30))

    # ------------------------------------------------------------ bookkeeping
    def _inventories(self, state):
        tot = self.cylinder.totals(state["cyl"], getattr(self, "_theta_now", self.theta_start))
        out = {"cylinder_mass": float(tot[:self.ns].sum()), "cylinder_energy": float(tot[self.ns + 1])}
        for name, d in self.ducts.items():
            inv = d.inventory(state["ducts"][name])
            out[f"{name}_mass"] = float(inv[:self.ns].sum())
            out[f"{name}_energy"] = float(inv[self.ns + 2])
        return out

    def _new_record(self, index, theta, state, rates):
        rec = CycleRecord(index, theta)
        rec.start_inventory = self._inventories(state)
        rec.work_by_stroke = {name: 0.0 for name, *_ in STROKES}
        for c in self.connections:
            rec.connection_mass[c.name] = [0.0, 0.0]
            rec.connection_species[c.name] = np.zeros(self.ns + 2)
            rec.choked_steps[c.name] = 0
        rec.trace = {k: [] for k in ("theta", "p", "T", "V", "mass", "xb", "burn", "h", "q_loss", "T_u", "T_b")}
        for c in self.connections:
            rec.trace[f"mdot_{c.name}"] = []
        for name in self.sensors:
            rec.trace[f"p_{name}"] = []
        for name in self.plenums:
            rec.trace[f"p_plenum_{name}"] = []
        for name in self.ducts:
            rec.trace[f"a_mean_{name}"] = []
        rec._burn_x = 0.0
        self._sample(rec, state, theta, rates)
        return rec

    def _accumulate(self, ledger, rec, r0, r1, dt, theta_a, theta_b, dx, rejected):
        half = 0.5 * dt
        ledger.reservoir_in += half * (r0["reservoir_in"] + r1["reservoir_in"])
        work = half * (r0["piston_power"] + r1["piston_power"])
        ledger.piston_work += work
        heat = half * (r0["heat_loss"] + r1["heat_loss"])
        ledger.cylinder_heat_loss += heat
        dheat = half * (r0["duct_heat"] + r1["duct_heat"])
        ledger.duct_heat_gain += dheat
        rec.work_net += work
        rec.heat_loss += heat
        rec.duct_heat_gain += dheat
        mid = wrap(0.5 * (theta_a + theta_b))
        for name, lo, hi in STROKES:
            if lo <= mid < hi:
                rec.work_by_stroke[name] += work
        for c in self.connections:
            e0, e1 = r0["exchange"][c.name], r1["exchange"][c.name]
            m0, m1 = -e0.mdot_into_duct, -e1.mdot_into_duct
            rec.connection_mass[c.name][0] += half * (max(m0, 0) + max(m1, 0))
            rec.connection_mass[c.name][1] += half * (max(-m0, 0) + max(-m1, 0))
            rec.connection_species[c.name] += half * (e0.to_volume + e1.to_volume)
            rec.choked_steps[c.name] += int(e1.choked)
        comb = self.cylinder.combustion
        if dx > 0 and self.cylinder.burn is not None:
            species_per_x, unburned = self.cylinder.burn
            ledger.tracer_source += unburned * dx
            rec.fuel_burned += -species_per_x[self.mix.index(comb.fuel)] * dx
            rec._burn_x += dx
        rec.steps += 1
        rec.rejected_steps += rejected

    def _sample(self, rec, state, theta, rates):
        g = rates["gas"]
        t = rec.trace
        t["theta"].append(theta - rec.theta_start + wrap(rec.theta_start))
        t["p"].append(g.p)
        t["T"].append(g.T)
        t["V"].append(rates["volume"])
        t["mass"].append(rates["mass"])
        t["xb"].append(g.xb)
        t["burn"].append(rec._burn_x if hasattr(rec, "_burn_x") else 0.0)
        t["h"].append(rates["h"])
        t["q_loss"].append(rates["heat_loss"])
        for c in self.connections:
            t[f"mdot_{c.name}"].append(-rates["exchange"][c.name].mdot_into_duct)
        for name, (duct, index) in self.sensors.items():
            t[f"p_{name}"].append(float(rates["prim"][duct]["p"][index]))
        for name, d in self.ducts.items():
            t[f"a_mean_{name}"].append(float(np.dot(rates["prim"][name]["a"], d.dx) / d.length))
        for name, gas in rates["plenum_gas"].items():
            t[f"p_plenum_{name}"].append(float(gas.p))
        zs = rates["zones"]
        t["T_u"].append(zs.T_u if zs is not None and zs.m_u > 0.0 else float("nan"))
        t["T_b"].append(zs.T_b if zs is not None else g.T)
        if g.p > rec.p_max:
            rec.p_max, rec.theta_p_max = g.p, t["theta"][-1]
        rec.T_max = max(rec.T_max, g.T, t["T_b"][-1])
        rec.T_b_max = max(rec.T_b_max, t["T_b"][-1])
        if math.isfinite(t["T_u"][-1]):
            rec.T_u_max = t["T_u"][-1] if not math.isfinite(rec.T_u_max) else max(rec.T_u_max, t["T_u"][-1])

    def _on_event(self, state, theta_abs, record):
        theta = wrap(theta_abs)
        if min(abs(theta - e) for e in self.events) > 1e-9:
            return state
        cyl = self.cylinder
        gas, m, V = cyl.gas(state["cyl"], theta)
        tot = cyl.totals(state["cyl"], theta)
        labels = []
        for label, valve in (("I", cyl.intake), ("E", cyl.exhaust)):
            if valve is not None:
                if abs(theta - valve.lift_law.open_deg) < 1e-9:
                    labels.append(label + "VO")
                if abs(theta - valve.lift_law.close_deg) < 1e-9:
                    labels.append(label + "VC")
        comb = cyl.combustion
        if comb is not None and abs(theta - wrap(comb.wiebe.start_deg)) < 1e-9:
            labels.append("SOC")
            mi = state["cyl"][:self.ns]
            fuel = comb.efficiency * mi[self.mix.index(comb.fuel)]
            delta = products_change(self.mix, comb.fuel, fuel, mi[self.mix.index("O2")], comb.water_gas_k)
            cyl.burn = (delta, m * (1.0 - gas.xb))
            if cyl.zones is not None:
                z2 = cyl.zones.begin(state["cyl"], gas, comb.wiebe, comb.fuel, comb.efficiency)
                if z2 is not None:
                    state = dict(state, cyl=z2)
        if comb is not None and abs(theta - wrap(comb.wiebe.start_deg + comb.wiebe.duration_deg)) < 1e-9:
            cyl.burn = None
        if cyl.intake is not None and abs(theta - cyl.intake.lift_law.close_deg) < 1e-9:
            cyl.woschni_reference = (gas.p, gas.T, V, gas.gamma)
        for label in labels:
            record.snapshots[label] = dict(theta=theta, p=gas.p, T=gas.T, mass=m, volume=V, xb=gas.xb,
                                           species=tot[:self.ns].tolist())
        merge_at = cyl.exhaust.lift_law.open_deg if cyl.exhaust is not None else 180.0
        if state["cyl"].size == 2 and abs(theta - wrap(merge_at)) < 1e-9:
            state = dict(state, cyl=cyl.zones.merge(state["cyl"], theta))
        return state

    def _finish_record(self, rec, keep_all):
        t = rec.trace
        theta = np.array(t["theta"])
        grid = np.arange(-360.0, 360.0, 1.0)
        rec.trace["pressure_grid"] = np.interp(grid, theta, np.array(t["p"])).tolist()
        rec.connection_species = {k: v.tolist() for k, v in rec.connection_species.items()}
