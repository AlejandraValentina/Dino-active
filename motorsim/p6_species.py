"""P6 passive four-species transport on the P5-C conservative backbone.

Species are bookkeeping fields only.  They do not alter the EOS or energy.
"""
from dataclasses import dataclass
from math import fsum, isfinite
from .p7_prescribed import Q_F, burn_fraction, capture_event, restore_event, snapshot_event

SPECIES = ("fresh_air", "fuel", "residual", "burned")


def validate_species(values, mass, *, tol=1e-14):
    values = tuple(float(x) for x in values)
    if len(values) != 4 or not isfinite(mass) or mass < 0:
        raise ValueError("invalid species state")
    if any(not isfinite(x) or x < -tol for x in values):
        raise ValueError("inadmissible species mass")
    if abs(fsum(values) - mass) > tol * max(1.0, mass):
        raise ValueError("species masses do not sum to total mass")
    return values


def donor_species(mass_flux, donor, receiver=None):
    """Return conservative species flux using the actual upstream donor."""
    if mass_flux > 0:
        source = donor
    elif mass_flux < 0:
        if receiver is None:
            raise ValueError("reverse flow requires receiver donor state")
        source = receiver
    else:
        return (0.0, 0.0, 0.0, 0.0)
    validate_species(source, fsum(source))
    return tuple(mass_flux * x / fsum(source) for x in source)


@dataclass
class SpeciesChamber:
    mass: float
    species: tuple

    def __post_init__(self):
        self.species = validate_species(self.species, self.mass)

    def apply(self, outward_species_flux, dt):
        if dt <= 0 or len(outward_species_flux) != 4:
            raise ValueError("invalid species update")
        values = tuple(a - dt * b for a, b in zip(self.species, outward_species_flux))
        self.species = validate_species(values, self.mass - dt * sum(outward_species_flux))
        self.mass -= dt * sum(outward_species_flux)


def advect_species(left, right, mass_flux, dt, volume):
    """Apply one shared interface mass flux to adjacent finite volumes."""
    if dt <= 0 or volume <= 0:
        raise ValueError("invalid transport step")
    flux = donor_species(mass_flux, left, right)
    lmass = fsum(left) - dt * mass_flux / volume
    rmass = fsum(right) + dt * mass_flux / volume
    lnew = tuple(a - dt * f / volume for a, f in zip(left, flux))
    rnew = tuple(a + dt * f / volume for a, f in zip(right, flux))
    return validate_species(lnew, lmass), validate_species(rnew, rmass), flux


def atmospheric_species():
    return (1.0, 0.0, 0.0, 0.0)


def legacy_to_species(mass, fresh_fraction=1.0):
    """Deterministic P5 compatibility mapping; no fabricated fuel history."""
    if mass < 0 or not 0.0 <= fresh_fraction <= 1.0:
        raise ValueError("invalid legacy composition")
    fresh = mass * fresh_fraction
    return (fresh, 0.0, mass - fresh, 0.0)


def legacy_fresh_mass(species):
    validate_species(species, fsum(species))
    return species[0] + species[1]


def scavenging_metrics(cylinder_species, transfer_fresh=0.0,
                       exhaust_outward_mass=0.0, donor_species_state=None):
    total = fsum(cylinder_species)
    fresh = legacy_fresh_mass(cylinder_species)
    donor = donor_species_state if donor_species_state is not None else cylinder_species
    fresh_fraction_donor = legacy_fresh_mass(donor) / fsum(donor) if fsum(donor) else 0.0
    short = max(0.0, exhaust_outward_mass) * fresh_fraction_donor
    return {
        "cylinder_fresh_mass": fresh,
        "cylinder_fresh_fraction": fresh / total if total else 0.0,
        "cylinder_residual_mass": cylinder_species[2],
        "cylinder_burned_mass": cylinder_species[3],
        "fresh_mass_delivered": max(0.0, transfer_fresh),
        "fresh_short_circuit_mass": short,
    }


class P6SpeciesLedger:
    """Independent global species inventory and external exchange ledger."""
    def __init__(self, components):
        self.initial = tuple(fsum(c[i] for c in components) for i in range(4))
        self.current = list(self.initial)
        self.external = [0.0] * 4
        self.steps = []

    def update(self, components, external_flux=(0.0, 0.0, 0.0, 0.0)):
        before = tuple(self.current)
        self.current = [fsum(c[i] for c in components) for i in range(4)]
        self.external = [a + b for a, b in zip(self.external, external_flux)]
        measured = tuple(b - a for a, b in zip(before, self.current))
        residual = tuple(d - e for d, e in zip(measured, external_flux))
        self.steps.append({
            "inventory_before": before,
            "inventory_after": tuple(self.current),
            "integrated_external_exchange": tuple(external_flux),
            "measured_inventory_change": measured,
            "residual": residual,
            "normalized_residual": tuple(r / max(1.0, abs(d), abs(e))
                                         for r, d, e in zip(residual, measured, external_flux)),
        })

    def report(self):
        delta = tuple(b - a for a, b in zip(self.initial, self.current))
        residual = tuple(d - e for d, e in zip(delta, self.external))
        return {name: {"initial": self.initial[i], "final": self.current[i],
                       "external": self.external[i], "residual": residual[i],
                       "steps": [{k: v[i] if isinstance(v, tuple) else v
                                  for k, v in step.items()}
                                 for step in self.steps]}
                for i, name in enumerate(SPECIES)}

    def cumulative_residuals(self):
        delta = tuple(b - a for a, b in zip(self.initial, self.current))
        residual = tuple(d - e for d, e in zip(delta, self.external))
        return {name: residual[i] for i, name in enumerate(SPECIES)}


class P6IntegratedSystem:
    """Species companion advanced at the two P5-C stage evaluations.

    The gas state is supplied by an ``IntegratedP5C`` instance.  This class
    keeps authoritative species masses and evaluates donor fluxes from each
    stage trace before the corresponding gas stage is installed.
    """
    def __init__(self, gas_system, *, component_species=None, capture_trace=False,
                 enable_p7=False, angular_rate_deg_s=18000.0):
        self.gas = gas_system
        self.capture_trace = bool(capture_trace)
        self.species = component_species or self._default_state()
        self.species_mass = self._mass_state_from_views()
        self._refresh_species_views()
        self._initial = self._species_totals()
        self._external = [0.0] * 4
        self.fresh_delivered = 0.0
        self.fresh_delivered_tr1 = 0.0
        self.fresh_delivered_tr2 = 0.0
        self.fresh_short_circuit = 0.0
        self._stage_active = False
        self._count_transport = True
        self.verification_trace = []
        self.external_flux_trace = []
        self.p7_event = None
        self.p7_events = []
        self.p7_source_delta = [0.0] * 4
        self.p7_enabled = bool(enable_p7)
        self.p7_angular_rate_deg_s = float(angular_rate_deg_s)
        if self.p7_enabled and self.p7_angular_rate_deg_s <= 0:
            raise ValueError("P7 angular rate must be positive")

    def _p7_source(self, theta, cylinder_q, port):
        if self.p7_event is None:
            return (0.0, 0.0, 0.0)
        if theta >= self.p7_event.start + 40.0:
            return (0.0, 0.0, 0.0)
        left, right = getattr(self, '_p7_active_interval', (theta, theta))
        # The prescribed event has a fixed 40-degree support.  Once the
        # interval is past its end, the event remains available for ledger
        # inspection/restart but must not keep injecting heat into later
        # measured angles.
        if right <= self.p7_event.start or left >= self.p7_event.start + 40.0:
            return (0.0, 0.0, 0.0)
        if 350.0 < theta < 390.0 and port['area'] != 0.0:
            raise ValueError("P7 heat event requires closed cylinder ports")
        # Reuse the authoritative species source so terminal inventory
        # limiting and gas heat use exactly the same SSPRK increment.
        rate = self._p7_species_source(theta)
        # P5-C's legacy fresh scalar is not authoritative for P6.  Do not
        # consume it here: P6 species_mass receives the source below with the
        # same SSPRK2 stage weighting.  The gas hook contributes heat only.
        return (0.0, rate[4], 0.0)

    def _p7_species_source(self, theta):
        left, right = self._p7_active_interval
        if self.p7_event is None:
            return (0.0, 0.0, 0.0, 0.0, 0.0)
        if theta >= self.p7_event.start + 40.0:
            return (0.0, 0.0, 0.0, 0.0, 0.0)
        if right <= self.p7_event.start or left >= self.p7_event.start + 40.0:
            return (0.0, 0.0, 0.0, 0.0, 0.0)
        from .p7_prescribed import burn_fraction
        dt = (right - left) / self.p7_angular_rate_deg_s
        if self._p7_mass_rate is not None:
            rate = self._p7_stage_mass(theta) / dt
        elif right >= self.p7_event.start + 40.0:
            mass = sum(self.species_mass['cylinder'][0][:2])
        else:
            progress = burn_fraction(right, self.p7_event.start) - burn_fraction(
                left, self.p7_event.start)
            mass = self.p7_event.fresh * progress
        if self._p7_mass_rate is None:
            rate = mass / dt
        return (-self.p7_event.alpha_air * rate,
                -self.p7_event.alpha_fuel * rate, 0.0, rate,
                Q_F * rate)

    def _p7_stage_mass(self, theta):
        """Return the bounded SSPRK2 stage increment for this segment."""
        mass = self._p7_mass_rate * (
            self._p7_active_interval[1] - self._p7_active_interval[0]) / self.p7_angular_rate_deg_s
        terminal = (self._p7_active_interval[1] >= self.p7_event.start + 40.0 - 1e-9 and
                    self.p7_event.ledger.burned_produced + mass >=
                    self.p7_event.fresh - 1e-12)
        if terminal and theta <= self._p7_active_interval[0] + 1e-12:
            return 0.0
        return 2.0 * mass if terminal else mass

    def _default_state(self):
        fresh = atmospheric_species()
        return {
            'crankcase': [fresh], 'cylinder': [fresh],
            'intake': [fresh for _ in self.gas.core.intake.cells],
            'tr1': [fresh for _ in self.gas.core.transfers[0].cells],
            'tr2': [fresh for _ in self.gas.core.transfers[1].cells],
            'exhaust': [fresh for _ in self.gas.exhaust.cells],
        }

    def _species_totals(self):
        return tuple(fsum(cell[i] for cells in self.species_mass.values() for cell in cells)
                     for i in range(4))

    def _gas_component_masses(self, component):
        if component in ('crankcase', 'cylinder'):
            return [getattr(self.gas.core, component).inventory(self.gas.eos)[0]]
        path = {'intake': self.gas.core.intake,
                'tr1': self.gas.core.transfers[0],
                'tr2': self.gas.core.transfers[1],
                'exhaust': self.gas.exhaust}[component]
        return [q[0] * v for q, v in zip(path.conservative(), path.mesh.volumes)]

    def _mass_state_from_views(self):
        return {name: [tuple(m * y for y in cell)
                       for m, cell in zip(self._gas_component_masses(name), cells)]
                for name, cells in self.species.items()}

    def _refresh_species_views(self):
        self.species = {
            name: [tuple(x / fsum(mass) for x in mass) if fsum(mass) else (0.0,) * 4
                   for mass in cells]
            for name, cells in self.species_mass.items()}

    def _sync_manual_views(self):
        """Accept initialization-time compatibility edits, then own masses."""
        self.species_mass = self._mass_state_from_views()
        self._refresh_species_views()

    def _views_match_authoritative_state(self):
        for name, cells in self.species.items():
            for view, mass in zip(cells, self.species_mass[name]):
                total = fsum(mass)
                expected = tuple(x / total for x in mass) if total else (0.0,) * 4
                if any(abs(a - b) > 1e-15 for a, b in zip(view, expected)):
                    return False
        return True

    def validate(self):
        for cells in self.species_mass.values():
            for cell in cells: validate_species(cell, fsum(cell))
        self._refresh_species_views()
        return True

    def derived_legacy_fresh(self, component):
        cells = self.species[component]
        return fsum(legacy_fresh_mass(c) for c in cells)

    def _step_segment(self, dt, *, angle=None):
        """Advance gas and species with stage snapshots from the same P5-C RHS."""
        # Species are updated from the exact stage interface traces exposed by
        # P5-C; no independent gas flux solve or legacy mY state is evolved.
        if not self._views_match_authoritative_state():
            self._sync_manual_views()
        before = self._species_totals()
        theta_end = (float(angle) if angle is not None else
                     self.gas.angle + float(dt) * self.p7_angular_rate_deg_s)
        theta_start = theta_end - float(dt) * self.p7_angular_rate_deg_s
        p7_step = (float(dt) * self.p7_angular_rate_deg_s
                   if self.p7_enabled else None)
        if (self.p7_enabled and self.p7_event is None and
                theta_start <= 350.0 < theta_end):
            self.p7_event = capture_event(350.0, self.species_mass['cylinder'][0])
            self.p7_events.append(self.p7_event)
        self._p7_active_interval = (theta_start, theta_end)
        self._p7_mass_rate = None
        p7_heat_before = (self.p7_event.ledger.heat_added
                          if self.p7_event is not None else 0.0)
        previous_totals = dict(self.gas._previous_totals)
        if self.p7_event is not None:
            lo, hi = max(theta_start, self.p7_event.start), min(theta_end, self.p7_event.start + 40.0)
            if hi > lo:
                target = self.p7_event.fresh * burn_fraction(hi, self.p7_event.start)
                available = sum(self.species_mass['cylinder'][0][:2])
                # The same bounded increment is used by both SSPRK2 stages.
                # In particular, do not replace it at the terminal boundary
                # by the stage-local remainder: that would apply the final
                # inventory twice before the SSPRK blend.
                mass = min(available, max(0.0,
                                          target - self.p7_event.ledger.burned_produced))
                self._p7_mass_rate = mass / dt
        record = self.gas.step(dt, angle=angle,
                               source=self._p7_source if self.p7_enabled else None,
                               angle_step=p7_step)
        # Consume both stage traces.  Each stage reads the currently updated
        # authoritative species state; no legacy scalar is cached.
        self.stage_species = []
        if not hasattr(self, 'verification_trace'):
            self.verification_trace = []
        if not hasattr(self, 'external_flux_trace'):
            self.external_flux_trace = []
        trace_start = len(self.verification_trace)
        species_q0 = {k: [tuple(x) for x in v] for k, v in self.species_mass.items()}
        self._count_transport = False
        self._stage_active = True
        for stage, interfaces in enumerate(record['core_interfaces']):
            before_stage = {k: [tuple(x) for x in v] for k, v in self.species.items()}
            before_mass_stage = {k: [tuple(x) for x in v] for k, v in self.species_mass.items()}
            stage_angle = theta_start if stage == 0 else theta_end
            if self.p7_event is not None and 350.0 <= stage_angle <= 390.0:
                source = self._p7_species_source(stage_angle)
                cylinder = self.species_mass['cylinder'][0]
                delta = tuple(dt * source[i] for i in range(4))
                updated = tuple(a + b for a, b in zip(cylinder, delta))
                if updated[0] < 0.0 or updated[1] < 0.0:
                    # Stage limiter: preserve the stage total while never
                    # allowing either captured reactant below zero.  This is
                    # only reachable at the terminal inventory boundary (or
                    # its floating-point representation).
                    consumed = max(0.0, cylinder[0]) - max(0.0, updated[0])
                    consumed += max(0.0, cylinder[1]) - max(0.0, updated[1])
                    updated = (max(0.0, updated[0]), max(0.0, updated[1]),
                               updated[2], cylinder[3] + consumed)
                    delta = tuple(a - b for a, b in zip(updated, cylinder))
                    source = tuple(x / dt for x in delta) + (Q_F * consumed / dt,)
                self.species_mass['cylinder'][0] = validate_species(
                    updated, fsum(updated))
                # SSPRK2 accumulated contribution is the stage-weighted half
                # sum; the authoritative species state is blended below.
                # Use the accepted burned-species increment for the matching
                # prescribed heat.  The source remains Q_F times burn rate;
                # tying both ledgers to the same accepted delta avoids a
                # floating-point split between mass and energy accounting.
                self.p7_event.record(tuple(0.5 * x for x in delta),
                                     0.5 * Q_F * delta[3])
                for i, value in enumerate(delta):
                    self.p7_source_delta[i] += 0.5 * value
                self._refresh_species_views()
            face_groups = record.get('stage_face_fluxes', ((), ()))[stage]
            for component, faces in zip(('intake', 'tr1', 'tr2'), face_groups):
                self._transport_internal_faces(component, faces, dt)
            self._transport_internal_faces('exhaust',
                                           record.get('stage_exhaust_faces', ((), ()))[stage],
                                           dt)
            interface_specs = ((interfaces[0], 'intake', 'crankcase'),
                               (interfaces[1], 'tr1', 'crankcase'),
                                                 (interfaces[2], 'tr2', 'crankcase'),
                                                 (interfaces[3], 'tr1', 'cylinder'),
                                                 (interfaces[4], 'tr2', 'cylinder'))
            stage_trace = []
            for flux, left_name, right_name in interface_specs:
                if self.capture_trace:
                    stage_trace.append(self._trace_interface(stage, left_name, right_name,
                                                             flux, before_stage))
                self._exchange(flux[0], left_name, right_name, dt)
            if stage < len(record.get('stage_interfaces', ())):
                pflux = record['stage_interfaces'][stage][2]
                physical_exhaust_flux = tuple(-x for x in pflux)
                if self.capture_trace:
                    stage_trace.append(self._trace_interface(stage, 'cylinder', 'exhaust',
                                                             physical_exhaust_flux, before_stage))
                self._exchange(physical_exhaust_flux[0], 'cylinder', 'exhaust', dt)
            self._boundary_exchange(record['stage_external'][stage][0], 'intake',
                                    dt, incoming=True)
            self._boundary_exchange(record.get('stage_exhaust_external',
                                               ((0.0, 0.0, 0.0, 0.0),) * 2)[stage][0],
                                    'exhaust', dt, incoming=False)
            if self.capture_trace:
                rhs_trace = self._stage_rhs_trace(
                    stage, interfaces, tuple(-x for x in record['stage_interfaces'][stage][2]),
                    before_stage)
                self.verification_trace.append({"step_index": len(getattr(self.gas, 'history', [])),
                                                "stage_index": stage, "interfaces": stage_trace,
                                                "rhs": rhs_trace})
                self.external_flux_trace.append(self._external_trace(stage, record, before_stage))
            self.stage_species.append({'before': before_stage,
                                       'after': {k: [tuple(x) for x in v]
                                                 for k, v in self.species.items()},
                                       'species_mass_before': before_mass_stage,
                                       'species_mass_after': {k: [tuple(x) for x in v]
                                                              for k, v in self.species_mass.items()}})
            if stage == 0:
                species_q1 = {k: [tuple(x) for x in v] for k, v in self.species_mass.items()}
            else:
                species_q2 = {k: [tuple(x) for x in v] for k, v in self.species_mass.items()}
        self.species_mass = {k: [tuple(0.5 * (a + c)
                                      for a, c in zip(species_q0[k][i], species_q2[k][i]))
                               for i in range(len(species_q0[k]))]
                             for k in species_q0}
        self._refresh_species_views()
        for trace in self.verification_trace[trace_start:]:
            for item in trace['interfaces']:
                value = item['gas_mass_flux'] * sum(item['donor_species_fractions'][name]
                                                   for name in ('fresh_air', 'fuel'))
                if item['interface_name'] == 'tr1<->cylinder' and value > 0:
                    self.fresh_delivered_tr1 += 0.5 * dt * value
                if item['interface_name'] == 'tr2<->cylinder' and value > 0:
                    self.fresh_delivered_tr2 += 0.5 * dt * value
                if item['interface_name'] == 'cylinder<->exhaust' and value > 0:
                    self.fresh_short_circuit += 0.5 * dt * value
        self.fresh_delivered = self.fresh_delivered_tr1 + self.fresh_delivered_tr2
        self.validate()
        self._stage_active = False
        self._count_transport = True
        after = self._species_totals()
        if self.p7_event is not None:
            accepted_heat = self.p7_event.ledger.heat_added - p7_heat_before
            heat_correction = accepted_heat - record['prescribed_heat']
            if heat_correction != 0.0:
                chamber = self.gas.core.cylinder
                mass, species, energy = chamber.inventory(self.gas.eos)
                energy += heat_correction
                if energy <= 0.0:
                    raise ValueError("P7 heat reconciliation produced inadmissible energy")
                chamber.primitive = (
                    mass / chamber.volume, 0.0,
                    (self.gas.eos.gamma - 1.0) * energy / chamber.volume,
                    species / mass)
                record['prescribed_heat'] = accepted_heat
                record['totals'] = self.gas.totals()
                self.gas._previous_totals = previous_totals
                record['ledger'] = self.gas.ledger_report(accepted_heat)
            # Close the durable gas history against the authoritative event
            # ledger at the exact event boundary.  This is an accounting
            # correction for summation order only; the P7 burn law and ledger
            # increments remain unchanged.
            if theta_end >= self.p7_event.start + 40.0:
                accumulated = sum(h['prescribed_heat'] for h in self.gas.history)
                accumulated += record['prescribed_heat']
                closure_correction = self.p7_event.ledger.heat_added - accumulated
                if closure_correction != 0.0:
                    chamber = self.gas.core.cylinder
                    mass, species, energy = chamber.inventory(self.gas.eos)
                    energy += closure_correction
                    if energy <= 0.0:
                        raise ValueError("P7 heat history closure produced inadmissible energy")
                    chamber.primitive = (
                        mass / chamber.volume, 0.0,
                        (self.gas.eos.gamma - 1.0) * energy / chamber.volume,
                        species / mass)
                    record['prescribed_heat'] += closure_correction
                    record['totals'] = self.gas.totals()
                    self.gas._previous_totals = previous_totals
                    record['ledger'] = self.gas.ledger_report(record['prescribed_heat'])
        return {'gas': record, 'species_initial': before,
                'species_final': after, 'legacy_fresh_cylinder': self.derived_legacy_fresh('cylinder'),
                'fresh_delivered': self.fresh_delivered,
                'fresh_delivered_tr1': self.fresh_delivered_tr1,
                'fresh_delivered_tr2': self.fresh_delivered_tr2,
                'fresh_short_circuit': self.fresh_short_circuit}

    def step(self, dt, *, angle=None):
        """Advance one physical step, splitting P7 exactly at event bounds."""
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        if not self.p7_enabled:
            return self._step_segment(dt, angle=angle)

        start = float(self.gas.angle)
        end = float(angle) if angle is not None else start + dt * self.p7_angular_rate_deg_s
        if end < start:
            raise ValueError("angle must not move backwards")
        points = [start]
        for boundary in (350.0, 390.0):
            if start < boundary < end:
                points.append(boundary)
        points.append(end)
        result = None
        for left, right in zip(points, points[1:]):
            segment_angle = right - left
            segment_dt = segment_angle / self.p7_angular_rate_deg_s
            result = self._step_segment(segment_dt, angle=right)
        return result

    def _external_trace(self, stage, record, state):
        core = record['core_interfaces'][stage]
        # P5-C stores the atmospheric inflow in the stage core trace and the
        # exhaust outlet in the stage port trace; both are already resolved.
        ext = record.get('stage_external', ((0.0, 0.0, 0.0, 0.0),
                                            (0.0, 0.0, 0.0, 0.0)))[stage]
        exhaust = record.get('stage_exhaust_external',
                             ((0.0, 0.0, 0.0, 0.0),) * 2)[stage]
        atmospheric = tuple(ext)
        atmosphere_state = atmospheric_species()
        intake_donor = state['intake'][0] if atmospheric[0] < 0 else atmosphere_state
        inflow_species = tuple(atmospheric[0] * x / fsum(intake_donor)
                               for x in intake_donor)
        exhaust_donor = state['exhaust'][-1] if exhaust[0] > 0 else atmosphere_state
        out_species = tuple(exhaust[0] * x / fsum(exhaust_donor)
                            for x in exhaust_donor)
        return {'stage_index': stage,
                'atmosphere_intake': {'gas_mass_flux': atmospheric[0],
                                      'donor_component': 'atmosphere' if atmospheric[0] >= 0 else 'intake',
                                      'species_flux': dict(zip(SPECIES, inflow_species))},
                'exhaust_atmosphere': {'gas_mass_flux': exhaust[0],
                                       'donor_component': 'exhaust' if exhaust[0] >= 0 else 'atmosphere',
                                      'species_flux': dict(zip(SPECIES, out_species))}}

    def _boundary_exchange(self, mass_flux, component, dt, *, incoming):
        if mass_flux == 0.0:
            return
        target = self.species_mass[component]
        index = 0 if incoming else -1
        current = target[index]
        donor = atmospheric_species() if (mass_flux > 0) == incoming else self.species[component][index]
        signed = mass_flux if incoming else -mass_flux
        flux = tuple(signed * value / fsum(donor) for value in donor)
        delta = tuple(dt * value for value in flux)
        target[index] = validate_species(tuple(a + b for a, b in zip(current, delta)),
                                         fsum(current) + sum(delta))
        self._refresh_species_views()

    def _transport_internal_faces(self, component, faces, dt):
        cells = self.species_mass[component]
        for index in range(1, len(faces) - 1):
            mass_flux = float(faces[index][0])
            if mass_flux == 0.0:
                continue
            donor_index = index - 1 if mass_flux > 0 else index
            donor = cells[donor_index]
            total = fsum(donor)
            fractions = tuple(x / total for x in donor) if total else (0.0,) * 4
            species_flux = tuple(mass_flux * x for x in fractions)
            delta = tuple(dt * x for x in species_flux)
            cells[index - 1] = validate_species(
                tuple(a - b for a, b in zip(cells[index - 1], delta)),
                fsum(cells[index - 1]) - sum(delta))
            cells[index] = validate_species(
                tuple(a + b for a, b in zip(cells[index], delta)),
                fsum(cells[index]) + sum(delta))
        self._refresh_species_views()

    def _trace_interface(self, stage, left_name, right_name, flux, state):
        mass_flux = float(flux[0])
        donor_name = left_name if mass_flux > 0 else right_name if mass_flux < 0 else None
        donor_other = right_name if donor_name == left_name else left_name
        donor_index = self._endpoint_index(donor_name, donor_other) if donor_name else 0
        donor = tuple(state[donor_name][donor_index]) if donor_name else (0.0,) * 4
        donor_mass = fsum(donor)
        fractions = tuple(x / donor_mass for x in donor) if donor_mass else (0.0,) * 4
        species_flux = tuple(mass_flux * x for x in fractions)
        return {"stage_index": stage, "interface_name": f"{left_name}<->{right_name}",
                "left_component": left_name, "right_component": right_name,
                "gas_mass_flux": mass_flux,
                "physical_flow_direction": "left_to_right" if mass_flux > 0 else
                    "right_to_left" if mass_flux < 0 else "closed",
                "donor_component": donor_name, "donor_mass": donor_mass,
                "donor_species_fractions": dict(zip(SPECIES, fractions)),
                "species_fluxes": dict(zip(SPECIES, species_flux)),
                "closed": mass_flux == 0.0}

    def _component_inventory(self, component):
        """Read-only physical inventory, using gas geometry and species fractions."""
        if component in ('crankcase', 'cylinder'):
            chamber = getattr(self.gas.core, component)
            mass = chamber.inventory(self.gas.eos)[0]
            masses = [mass]
        else:
            path = {'intake': self.gas.core.intake,
                    'tr1': self.gas.core.transfers[0],
                    'tr2': self.gas.core.transfers[1],
                    'exhaust': self.gas.exhaust}[component]
            masses = [q[0] * v for q, v in zip(path.conservative(), path.mesh.volumes)]
        cells = self.species_mass[component]
        species_mass = tuple(fsum(cell[i] for cell in cells) for i in range(4))
        gas_mass = fsum(masses)
        return {'gas_mass': gas_mass,
                **{name + '_mass': species_mass[i] for i, name in enumerate(SPECIES)},
                'species_sum': fsum(species_mass),
                'species_sum_minus_gas_mass': fsum(species_mass) - gas_mass,
                'cells': [{'gas_mass': m,
                           **{name + '_mass': cell[i]
                              for i, name in enumerate(SPECIES)},
                           'species_sum_minus_gas_mass': fsum(cell) - m}
                          for m, cell in zip(masses, cells)]}

    def inventory_snapshot(self):
        names = ('crankcase', 'cylinder', 'intake', 'tr1', 'tr2', 'exhaust')
        components = {name: self._component_inventory(name) for name in names}
        totals = {key: fsum(item[key] for item in components.values())
                  for key in ('gas_mass', *(name + '_mass' for name in SPECIES),
                              'species_sum')}
        totals['species_sum_minus_gas_mass'] = totals['species_sum'] - totals['gas_mass']
        return {'components': components, 'global': totals}

    def _species_flux(self, flux, left, right, state):
        mass = float(flux[0])
        donor_name = left if mass > 0 else right if mass < 0 else None
        donor_other = right if donor_name == left else left
        donor_index = self._endpoint_index(donor_name, donor_other) if donor_name else 0
        donor = tuple(self.species_mass[donor_name][donor_index]) if donor_name else (0.0,) * 4
        total = fsum(donor)
        fractions = tuple(x / total for x in donor) if total else (0.0,) * 4
        return tuple(mass * x for x in fractions)

    def _stage_rhs_trace(self, stage, interfaces, port, before):
        specs = ((interfaces[0], 'intake', 'crankcase'),
                 (interfaces[1], 'tr1', 'crankcase'),
                 (interfaces[2], 'tr2', 'crankcase'),
                 (interfaces[3], 'tr1', 'cylinder'),
                 (interfaces[4], 'tr2', 'cylinder'),
                 (port, 'cylinder', 'exhaust'))
        contributions = {name: [0.0] * 4 for name in ('crankcase', 'cylinder')}
        records = []
        for flux, left, right in specs:
            sf = self._species_flux(flux, left, right, before)
            records.append({'interface_name': f'{left}<->{right}',
                            'species_flux': dict(zip(SPECIES, sf))})
            if left == 'crankcase':
                target = 'crankcase'
                sign = 1.0
            elif right == 'crankcase':
                target = 'crankcase'
                sign = -1.0
            elif left == 'cylinder':
                target = 'cylinder'
                sign = 1.0
            else:
                target = 'cylinder'
                sign = -1.0
            for i, value in enumerate(sf):
                contributions[target][i] += sign * value
        return {'stage_index': stage, 'interfaces': records,
                'crankcase': {'contributions': contributions['crankcase'][:],
                              'assembled_rhs': contributions['crankcase'][:]},
                'cylinder': {'contributions': contributions['cylinder'][:],
                             'assembled_rhs': contributions['cylinder'][:]}}

    def _exchange(self, mass_flux, left, right, dt):
        if mass_flux == 0.0: return
        if not self._stage_active and not self._views_match_authoritative_state():
            self._sync_manual_views()
        donor_name = left if mass_flux > 0 else right
        donor = self.species_mass[donor_name]
        donor_index = self._endpoint_index(donor_name, right if donor_name == left else left)
        source = donor[donor_index]
        flux = tuple(mass_flux * x / fsum(source) for x in source) if fsum(source) else (0.0,) * 4
        dm = tuple(dt*x for x in flux)
        left_index = self._endpoint_index(left, right)
        right_index = self._endpoint_index(right, left)
        self.species_mass[left][left_index] = validate_species(
            tuple(a-b for a,b in zip(self.species_mass[left][left_index], dm)),
            fsum(self.species_mass[left][left_index])-sum(dm))
        self.species_mass[right][right_index] = validate_species(
            tuple(a+b for a,b in zip(self.species_mass[right][right_index], dm)),
            fsum(self.species_mass[right][right_index])+sum(dm))
        self._refresh_species_views()

    @staticmethod
    def _endpoint_index(component, other):
        if component == 'intake' and other == 'crankcase':
            return -1
        if component in ('tr1', 'tr2'):
            return -1 if other == 'cylinder' else 0
        if component == 'exhaust' and other == 'cylinder':
            return 0
        return 0
        if self._count_transport and left in ('tr1', 'tr2') and right == 'cylinder' and mass_flux > 0:
            fresh = sum(dm[:2])
            self.fresh_delivered += fresh
            if left == 'tr1':
                self.fresh_delivered_tr1 += fresh
            else:
                self.fresh_delivered_tr2 += fresh
        if self._count_transport and left == 'cylinder' and right == 'exhaust' and mass_flux > 0:
            self.fresh_short_circuit += sum(dm[:2])

    def snapshot(self):
        return {'gas': self.gas.snapshot(),
                'species_mass': {k: [tuple(x) for x in v] for k,v in self.species_mass.items()},
                'external': list(self._external), 'fresh_delivered': self.fresh_delivered,
                'species_initial': tuple(self._initial),
                'fresh_delivered_tr1': self.fresh_delivered_tr1,
                'fresh_delivered_tr2': self.fresh_delivered_tr2,
                'fresh_short_circuit': self.fresh_short_circuit,
                'p7_event': snapshot_event(self.p7_event) if self.p7_event else None,
                'p7_source_delta': list(self.p7_source_delta),
                'p7_enabled': self.p7_enabled,
                'p7_angular_rate_deg_s': self.p7_angular_rate_deg_s}

    def restore(self, snapshot):
        self.gas.restore(snapshot['gas'])
        raw = snapshot.get('species_mass', snapshot.get('species'))
        if 'species_mass' in snapshot:
            self.species_mass = {k: [tuple(x) for x in v] for k,v in raw.items()}
        else:
            self.species = {k: [tuple(x) for x in v] for k,v in raw.items()}
            self.species_mass = self._mass_state_from_views()
        self._refresh_species_views()
        self._external = list(snapshot['external'])
        self._initial = tuple(snapshot.get('species_initial', self._initial))
        self.fresh_delivered = snapshot['fresh_delivered']
        self.fresh_delivered_tr1 = snapshot.get('fresh_delivered_tr1', 0.0)
        self.fresh_delivered_tr2 = snapshot.get('fresh_delivered_tr2', 0.0)
        self.fresh_short_circuit = snapshot['fresh_short_circuit']
        self.p7_event = restore_event(snapshot['p7_event']) if snapshot.get('p7_event') else None
        self.p7_events = [self.p7_event] if self.p7_event else []
        self.p7_source_delta = list(snapshot.get('p7_source_delta', [0.0] * 4))
        self.p7_enabled = bool(snapshot.get('p7_enabled', self.p7_enabled))
        self.p7_angular_rate_deg_s = float(snapshot.get('p7_angular_rate_deg_s',
                                                          self.p7_angular_rate_deg_s))

    def species_sum_error(self):
        """Cross-check authoritative species totals against gas mass."""
        return sum(self._species_totals()) - self.gas.totals()['mass']
