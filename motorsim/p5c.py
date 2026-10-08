"""Bounded P5-C intake/transfer/exhaust integration.

This module is deliberately small: it composes the verified P5-B finite
topology with the existing P4 port flux and gas1d Riemann primitives.  It is a
conditional verification fixture, not a periodic engine solver.
"""
from copy import deepcopy
from math import fsum, isfinite

from .p5b import IntegratedIntakeTransfer, Chamber, DuctCell, _FinitePath
from .coupling import ChamberState
from .exhaust_port import port_flux
from .gas1d.eos import IdealGas
from .gas1d.mesh import uniform_mesh
from .gas1d.riemann import hllc_flux
from .gas1d.boundary import Boundary


class IntegratedP5C:
    """Short-horizon coupled fixture with one finite exhaust path.

    ``step`` advances the already assembled P5-B state and then applies the
    same resolved cylinder/exhaust face flux to both connected components.
    The trace and ledgers make the conditional boundary explicit.
    """
    dependency_status = "CONDITIONAL_ON_P4"

    def __init__(self, crankcase, cylinder, duct_states, exhaust_states=None,
                 *, eos=None, meshes=None, exhaust_mesh=None,
                 exhaust_area=1.0e-4, port_area=0.0, volume_rates=(0.0, 0.0),
                 external_boundary=False, geometry_callback=None,
                 external_boundary_flux_convention="legacy_contract",
                 external_boundary_model=None):
        self.eos = eos or IdealGas()
        self.external_boundary_model = external_boundary_model
        self.core = IntegratedIntakeTransfer(crankcase, cylinder, duct_states,
                                             eos=self.eos, meshes=meshes,
                                             volume_rates=volume_rates,
                                             geometry_callback=geometry_callback,
                                             external_boundary=external_boundary,
                                             external_boundary_flux_convention=(
                                                 external_boundary_flux_convention),
                                             external_boundary_model=external_boundary_model)
        if exhaust_states is None:
            exhaust_states = ((1.0, 0.0, 100000.0, 0.0),) * 3
        self.exhaust_mesh = exhaust_mesh or uniform_mesh(len(exhaust_states),
                                                          length=0.03,
                                                          area=exhaust_area)
        self.exhaust = _FinitePath(exhaust_states, self.exhaust_mesh, self.eos)
        self.exhaust_area = float(exhaust_area)
        self.port_area = float(port_area)
        self.geometry_callback = geometry_callback
        self.angle = 0.0
        self.ledger = {"external_mass": 0.0, "external_energy": 0.0,
                       "external_species": 0.0, "port_mass": 0.0,
                       "port_energy": 0.0, "port_species": 0.0}
        self.history = []
        self._initial = self.totals()
        self._last_external = {"mass": 0.0, "energy": 0.0, "species": 0.0}
        self._external_cumulative = {"mass": 0.0, "energy": 0.0, "species": 0.0}
        self._previous_totals = dict(self._initial)

    def _duct_totals(self, path):
        return {"mass": fsum(q[0] * v for q, v in
                              zip(path.conservative(), path.mesh.volumes)),
                "energy": fsum(q[2] * v for q, v in
                                zip(path.conservative(), path.mesh.volumes)),
                "species": fsum(q[3] * v for q, v in
                                 zip(path.conservative(), path.mesh.volumes))}

    def totals(self):
        total = self.core._totals()
        ex = self._duct_totals(self.exhaust)
        return {k: total[k] + ex[k] for k in total}

    def admissible(self):
        self.core.admissible()
        for q in self.exhaust.conservative():
            self.eos.primitive_with_mass_fraction_roundoff(q)
        return True

    def _exhaust_step(self, dt):
        cyl_inv = self.core.cylinder.inventory(self.eos)
        chamber = ChamberState(cyl_inv[0], cyl_inv[2], cyl_inv[1],
                               self.core.cylinder.volume)
        first = self.eos.primitive_with_mass_fraction_roundoff(
            self.exhaust.cells[0].conservative)
        face = port_flux(chamber, first, self.port_area, self.exhaust_area,
                         eos=self.eos)
        flux = face["flux"]
        # Positive flux leaves the cylinder and enters the duct.
        self.core.cylinder.apply_rhs((-flux[0], -flux[2], -flux[3]), dt,
                                     self.eos)
        self.exhaust.cells[0].apply_flux(flux, dt, self.eos, sign=1.0)
        for i in range(len(self.exhaust.cells) - 1):
            a = self.eos.primitive_with_mass_fraction_roundoff(
                self.exhaust.cells[i].conservative)
            b = self.eos.primitive_with_mass_fraction_roundoff(
                self.exhaust.cells[i + 1].conservative)
            f, _, _ = hllc_flux(a, b, self.eos)
            extensive = tuple(self.exhaust_mesh.areas[i + 1] * x for x in f)
            self.exhaust.cells[i].apply_flux(extensive, dt, self.eos, sign=-1.0)
            self.exhaust.cells[i + 1].apply_flux(extensive, dt, self.eos, sign=1.0)
        outlet = self.eos.primitive_with_mass_fraction_roundoff(
            self.exhaust.cells[-1].conservative)
        outlet_boundary = self.external_boundary_model or Boundary("outflow")
        out = outlet_boundary.flux(outlet, 1, self.eos)[0]
        ext = tuple(self.exhaust_mesh.areas[-1] * x for x in out)
        self.exhaust.cells[-1].apply_flux(ext, dt, self.eos, sign=-1.0)
        for key, idx in (("external_mass", 0), ("external_energy", 2),
                         ("external_species", 3)):
            self.ledger[key] += dt * ext[idx]
        for key, idx in (("port_mass", 0), ("port_energy", 2),
                         ("port_species", 3)):
            self.ledger[key] += dt * flux[idx]
        return {"flux": flux, "closed": face["area"] == 0.0,
                "external": ext, "area": face["area"]}

    def _state(self):
        return self.core._state() + (self.exhaust.conservative(),)

    def _exhaust_rhs(self, q, cyl_q, dt_angle, stage_angle=None):
        """Return exhaust duct RHS and its single cylinder-facing flux."""
        chamber = ChamberState(cyl_q[0], cyl_q[2], cyl_q[3], cyl_q[4])
        prim = [self.eos.primitive_with_mass_fraction_roundoff(x) for x in q]
        exhaust_area = self.exhaust_area
        if self.geometry_callback is not None:
            geometry = self.geometry_callback(float(self.angle if stage_angle is None else stage_angle))
            areas = geometry['areas'] if isinstance(geometry, dict) else geometry[2]
            if len(areas) >= 4:
                exhaust_area = float(areas[3])
        # Legacy mode uses the historical explicit geometric ``port_area``.
        # A geometry callback supplies the dynamic geometric exhaust area and
        # the fixed constructor exhaust area remains the pipe limit.
        geometric_area = exhaust_area if self.geometry_callback is not None else self.port_area
        pipe_area = self.exhaust_area
        face = port_flux(chamber, prim[0], geometric_area, pipe_area,
                         eos=self.eos)
        faces = [face['flux']]
        for a, b, area in zip(prim, prim[1:], self.exhaust_mesh.areas[1:]):
            f, _, _ = hllc_flux(a, b, self.eos)
            faces.append(tuple(area * x for x in f))
        outlet_boundary = self.external_boundary_model or Boundary('outflow')
        out = outlet_boundary.flux(prim[-1], 1, self.eos)[0]
        faces.append(tuple(self.exhaust_mesh.areas[-1] * x for x in out))
        rhs = tuple(tuple(-(faces[i + 1][k] - faces[i][k]) /
                          self.exhaust_mesh.volumes[i] for k in range(4))
                    for i in range(len(q)))
        return rhs, face, faces[-1], tuple(faces)

    def _stage_rhs(self, state, *, stage_angle=None, source=None):
        core_state = state[:-1]
        core_rhs, trace = self.core._rhs(core_state, self.angle if stage_angle is None else stage_angle)
        ex_rhs, port, external, exhaust_faces = self._exhaust_rhs(
            state[-1], state[1], 0.0, stage_angle)
        # One cylinder RHS: P5-B TR1/TR2 terms plus this same exhaust flux.
        cyl = core_rhs[1]
        cyl = (cyl[0] - port['flux'][0],
               cyl[1] - port['flux'][2], cyl[2] - port['flux'][3])
        prescribed = (0.0, 0.0, 0.0) if source is None else tuple(
            source(self.angle if stage_angle is None else stage_angle, state[1], port))
        if len(prescribed) != 3:
            raise ValueError("cylinder source must return (dm, dU, dF)")
        cyl = tuple(a + b for a, b in zip(cyl, prescribed))
        return (core_rhs[0], cyl, core_rhs[2], core_rhs[3], core_rhs[4], ex_rhs), {
            'core': trace, 'port': port, 'external': external,
            'exhaust_faces': exhaust_faces,
            'cylinder_rhs': cyl, 'transfer_rhs': (core_rhs[1],),
            'prescribed_source': prescribed,
            'cylinder_interfaces': (trace['interfaces'][3], trace['interfaces'][4],
                                    tuple(-x for x in port['flux'])),
        }

    @staticmethod
    def _add_state(state, rhs, dt):
        out = []
        for q, r in zip(state, rhs):
            if isinstance(q, tuple) and q and isinstance(q[0], (int, float)):
                if len(q) == 5:
                    out.append((q[0] + dt*r[0], q[1], q[2] + dt*r[1],
                                q[3] + dt*r[2], q[4]))
                else:
                    out.append(tuple(a + dt*b for a, b in zip(q, r)))
            else:
                out.append(tuple(tuple(a + dt*b for a, b in zip(cell, dr))
                                 for cell, dr in zip(q, r)))
        return tuple(out)

    @staticmethod
    def _blend(a, b, rb, dt):
        out = []
        for qa, qb, rr in zip(a, b, rb):
            if qa and isinstance(qa[0], (int, float)):
                if len(qa) == 5 and len(rr) == 3:
                    out.append((.5*(qa[0]+qb[0]+dt*rr[0]), qa[1],
                                .5*(qa[2]+qb[2]+dt*rr[1]),
                                .5*(qa[3]+qb[3]+dt*rr[2]),
                                .5*(qa[4]+qb[4])))
                else:
                    out.append(tuple(.5*(x+y+dt*z) for x,y,z in zip(qa,qb,rr)))
            else:
                out.append(tuple(tuple(.5*(x+y+dt*z) for x,y,z in zip(x0,x1,r))
                                 for x0,x1,r in zip(qa,qb,rr)))
        return tuple(out)

    def _install(self, state):
        cc, cy, intake, tr1, tr2, exhaust = state
        self.core.crankcase.volume, self.core.cylinder.volume = cc[4], cy[4]
        for chamber, q in ((self.core.crankcase, cc), (self.core.cylinder, cy)):
            chamber.primitive = (q[0]/q[4], 0.0,
                                 (self.eos.gamma-1)*q[2]/q[4], q[3]/q[0])
        for path, values in zip((self.core.intake, *self.core.transfers),
                                (intake, tr1, tr2)):
            for cell, q in zip(path.cells, values): cell.conservative = q
        for cell, q in zip(self.exhaust.cells, exhaust): cell.conservative = q

    def step(self, dt, *, angle=None, port_area=None, source=None, angle_step=None):
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        previous_angle = float(self.angle)
        if port_area is not None:
            self.port_area = float(port_area)
        if angle is None:
            self.angle += float(dt) if angle_step is None else float(angle_step)
        else:
            self.angle = float(angle)
        stage_angle0 = self.angle - (float(dt) if angle_step is None else float(angle_step))
        q0 = self._state()
        def install_volumes(state, volumes):
            if volumes is None:
                return state
            cc, cy, *ducts = state
            return ((*cc[:4], volumes[1]), (*cy[:4], volumes[2]), *ducts)
        if self.geometry_callback is not None:
            geometry0 = self.geometry_callback(float(stage_angle0))
            volumes0 = geometry0['volumes'] if isinstance(geometry0, dict) else geometry0[0]
            q0 = install_volumes(q0, volumes0)
        r0, t0 = self._stage_rhs(q0, stage_angle=stage_angle0, source=source)
        q1 = self._add_state(q0, r0, dt)
        if self.geometry_callback is not None:
            geometry = self.geometry_callback(float(self.angle))
            volumes = geometry['volumes'] if isinstance(geometry, dict) else geometry[0]
            q1 = install_volumes(q1, volumes)
        r1, t1 = self._stage_rhs(q1, stage_angle=self.angle, source=source)
        qn = self._blend(q0, q1, r1, dt)
        if self.geometry_callback is not None:
            qn = install_volumes(qn, volumes)
        self._install(qn)
        self.admissible()
        trace = {'flux': t1['port']['flux'], 'closed': t1['port']['area'] == 0.0,
                 'external': t1['external'], 'area': t1['port']['area']}
        record = {"angle": self.angle, "exhaust": trace,
                  "stage_states": (q0, q1, qn),
                  "stage_rhs": (t0['cylinder_rhs'], t1['cylinder_rhs']),
                  "stage_interfaces": (t0['cylinder_interfaces'], t1['cylinder_interfaces']),
                  "core_interfaces": (t0['core']['interfaces'], t1['core']['interfaces']),
                  "stage_face_fluxes": (t0['core']['face_fluxes'], t1['core']['face_fluxes']),
                  "stage_external": (t0['core']['external'], t1['core']['external']),
                  "stage_exhaust_external": (t0['external'], t1['external']),
                  "stage_exhaust_faces": (t0['exhaust_faces'], t1['exhaust_faces']),
                  "stage_work_rates": (t0['core']['work_rates'], t1['core']['work_rates']),
                  "prescribed_heat": 0.5 * (t0['prescribed_source'][1] + t1['prescribed_source'][1]) * dt,
                  "totals": self.totals(), "dependency": self.dependency_status}
        # The coupled system has two external boundaries: the atmospheric
        # intake in the P5-C core trace and the exhaust outlet trace.  The
        # The core trace is positive into the stored topology.  The exhaust
        # outlet trace is positive out of it, so it enters the stored-system
        # exchange with the opposite sign.  Internal interfaces still cancel.
        self._last_external = {
            key: 0.5 * (t0['core']['external'][index] +
                        t1['core']['external'][index] -
                        t0['external'][index] - t1['external'][index]) * dt
            for key, index in (("mass", 0), ("energy", 2), ("species", 3))}
        for key in self._external_cumulative:
            self._external_cumulative[key] += self._last_external[key]
        record['dt'] = float(dt)
        record['angle_start'] = previous_angle
        record['ledger'] = self.ledger_report(record['prescribed_heat'])
        self.history.append(record)
        return record

    def ledger_report(self, prescribed_heat=0.0):
        final = self.totals()
        delta = {k: final[k] - self._initial[k] for k in final}
        ext = dict(self._last_external)
        residual = {k: delta[k] - self._external_cumulative[k]
                    for k in ('mass','energy','species')}
        residual['energy_without_prescribed_heat'] = residual['energy'] - prescribed_heat
        step_delta = {k: final[k] - self._previous_totals[k] for k in final}
        step_residual = {k: step_delta[k] - self._last_external[k]
                         for k in ('mass','energy','species')}
        self._previous_totals = dict(final)
        return {"prescribed_heat": prescribed_heat,
                "energy_balance_terms": {"external_conservative_exchange": ext['energy'],
                                           "prescribed_heat": prescribed_heat},
                "initial": dict(self._initial), "final": final, "delta": delta,
                "external": dict(self._external_cumulative), "step_external": ext,
                "residual": residual, "step_delta": step_delta,
                "step_residual": step_residual}

    def snapshot(self):
        return {"core": self.core.snapshot(), "exhaust": deepcopy(self.exhaust),
                "angle": self.angle, "port_area": self.port_area,
                "ledger": dict(self.ledger), "history": deepcopy(self.history),
                "initial": dict(self._initial), "previous": dict(self._previous_totals),
                "external_cumulative": dict(self._external_cumulative)}

    def restore(self, snapshot):
        self.core.restore(snapshot["core"])
        self.exhaust = deepcopy(snapshot["exhaust"])
        self.angle = snapshot["angle"]
        self.port_area = snapshot["port_area"]
        self.ledger = dict(snapshot["ledger"])
        self.history = deepcopy(snapshot["history"])
        self._initial = dict(snapshot.get("initial", self._initial))
        self._previous_totals = dict(snapshot.get("previous", self._initial))
        self._external_cumulative = dict(snapshot.get("external_cumulative", {
            "mass": 0.0, "energy": 0.0, "species": 0.0}))


def make_p5c_fixture(*, eos=None, cells=2, port_area=0.0):
    eos = eos or IdealGas()
    state = (1.0, 0.0, 100000.0, 0.2)
    ducts = tuple((state,) * cells for _ in range(3))
    crankcase = Chamber((1.0, 0.0, 105000.0, 0.3), 1.0e-3)
    cylinder = Chamber((1.0, 0.0, 100000.0, 0.2), 1.0e-2)
    return IntegratedP5C(crankcase, cylinder, ducts, (state,) * cells,
                         eos=eos, port_area=port_area)


def make_p5c_full_fixture(*, eos=None, cells=2, port_area=1.0e-4):
    """Full short topology with the atmospheric intake boundary enabled."""
    fixture = make_p5c_fixture(eos=eos, cells=cells, port_area=port_area)
    # Match the reservoir stagnation state at the intake boundary.  The
    # generic fixture's 100 kPa/implicit-temperature state requests a hotter
    # supersonic-compatible inflow and is outside Boundary('reservoir').
    rho = 101325.0 / (fixture.eos.R * 300.0)
    for cell in fixture.core.intake.cells:
        cell.conservative = fixture.eos.conservative((rho, 0.0, 101325.0, 0.0))
    fixture.core.external_boundary = True
    fixture._initial = fixture.totals()
    return fixture


def make_p5c_backflow_fixture(*, eos=None):
    """Controlled reverse-flow case at the crankcase/TR1 interface."""
    fixture = make_p5c_fixture(eos=eos, port_area=0.0)
    fixture.core.crankcase.primitive = (1.0, 0.0, 1.0e6, 0.2)
    fixture.core.transfers[0].cells[0].conservative = fixture.eos.conservative(
        (1.0, 0.0, 1.0e5, 0.8))
    fixture._initial = fixture.totals()
    return fixture
