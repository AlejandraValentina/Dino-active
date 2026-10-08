"""Duplicación RK4 autorizada; física y aceptación en simulation permanecen iguales."""
from dataclasses import asdict, dataclass
import math
import time
from collections import deque

from .simulation import (Model, SIZE, CV, BURN, WORK, HEAT, InvalidStage, StopCalculation,
                         rk4, burn_fraction, independent_increment, audit,
                         balances_ok, convergence, sample, TWO_LAYOUT)

MIN_SUBSTEP = .001


@dataclass(frozen=True)
class Profile:
    name: str
    max_step_deg: float
    rtol: float
    atol_mass: float
    atol_energy: float


PROFILES = (Profile('A', .5, 1e-6, 1e-12, 1e-6),
            Profile('B', .25, 3e-7, 3e-13, 3e-7),
            Profile('C', .125, 1e-7, 1e-13, 1e-7))


def error_norm(start, full, halves, profile, layout=TWO_LAYOUT):
    ratios = []
    for j in range(layout.physical):
        atol = profile.atol_energy if j % 3 == 1 else profile.atol_mass
        scale = atol + profile.rtol * max(abs(start[j]), abs(halves[j]))
        value = abs(halves[j]-full[j])/15/scale
        ratios.append(value if math.isfinite(value) else math.inf)
    worst = max(range(layout.physical), key=ratios.__getitem__)
    return ratios[worst], f'{layout.cv[worst//3]}.{("m", "U", "F")[worst%3]}'


def step_factor(error, rejected=False):
    if not math.isfinite(error) or error < 0:
        return .2
    factor = 2. if error == 0 else min(2., max(.2, .9*error**(-.2)))
    return min(.9, factor) if rejected else factor


def targets(begin, end, phases, period=360):
    # Coincidencias de eventos calculados y nodos: solo redondeo de máquina,
    # nunca fusionar intervalos físicos para esquivar el mínimo de paso.
    values = sorted({begin+i*.5 for i in range(1, 2*period+1)} |
                    {turn*period+p for turn in range(int(begin//period), int(end//period)+1)
                     for p in phases if begin < turn*period+p <= end})
    result = []
    for value in values:
        nearest = round(value*2)/2
        if abs(value-nearest) <= 8*math.ulp(value):
            value = nearest
        if not result or value != result[-1]:
            result.append(value)
    return result


class Stepper:
    def __init__(self, model, profile, trace=lambda row: None):
        self.model, self.profile, self.trace = model, profile, trace
        self.proposed = profile.max_step_deg
        self.rhs_count = self.attempts = self.accepted = 0
        self.stage_evaluations = self.endpoint_evaluations = 0
        self.rejections = dict(local_error=0, nonphysical=0, nonfinite_error=0)
        self.minimum = math.inf
        self.maximum = self.total = 0.

    def evaluate(self, angle, state, heat, stage=False):
        # Model.evaluate calcula derivadas incluso cuando solo se usa su snapshot.
        # Contar también esas evaluaciones, sin esconderlas detrás del nominal 12.
        if self.rhs_count >= 2_000_000:
            raise StopCalculation('límite de 2000000 evaluaciones RHS')
        self.rhs_count += 1
        if stage:
            self.stage_evaluations += 1
        else:
            self.endpoint_evaluations += 1
        return self.model.evaluate(angle, state, heat)

    def advance(self, angle, state, event, heat, check=lambda: None):
        remaining = event-angle
        h = min(self.proposed, self.profile.max_step_deg, remaining)
        # No dejar un resto que obligue a ejecutar medios pasos menores al mínimo.
        if 0 < remaining-h < 2*MIN_SUBSTEP:
            # Acortar, nunca superar la propuesta del controlador para cubrirlo.
            h = remaining/2
        failures = 0
        while True:
            check()
            if h/2 < MIN_SUBSTEP:
                raise StopCalculation(f'paso mínimo: propuesta {h:.12g}°, medio paso {h/2:.12g}° '
                                      f'a {angle:.9f}°')
            endpoint = angle+h if h < remaining else event
            dt = h/self.model.rate
            self.attempts += 1
            cause, error, worst = '', math.inf, ''
            def rhs(t, y):
                return self.evaluate(angle+t*self.model.rate, y, heat, stage=True)[0]
            def project(t, y):
                return self.model.analytic(angle+t*self.model.rate, y, heat)
            def step(t, y, length):
                result = rk4(t, y, length, rhs, project)
                a, b = angle+t*self.model.rate, angle+(t+length)*self.model.rate
                converted = (heat[1]*(burn_fraction(b, heat[0])-burn_fraction(a, heat[0])) if heat else 0.)
                result[self.model.layout.burn] = y[self.model.layout.burn]+converted
                snapshot = self.evaluate(b, result, heat)[1]
                return result, snapshot
            try:
                full, _ = step(0., state.copy(), dt)
                middle, middle_snapshot = step(0., state.copy(), dt/2)
                fine, fine_snapshot = step(dt/2, middle, dt/2)
                error, worst = error_norm(state, full, fine, self.profile, self.model.layout)
                if not math.isfinite(error):
                    cause = 'nonfinite_error'
                elif error > 1:
                    cause = 'local_error'
            except InvalidStage as exc:
                cause, worst = 'nonphysical', str(exc)
            self.trace(dict(angle_deg=angle, proposed_deg=h, substep_deg=h/2,
                            error=error if math.isfinite(error) else None, worst=worst,
                            accepted=not cause, cause=cause, rhs=self.rhs_count))
            if not cause:
                self.accepted += 2
                self.minimum, self.maximum = min(self.minimum, h/2), max(self.maximum, h/2)
                self.total += h
                self.proposed = min(self.profile.max_step_deg, h*step_factor(error))
                return [(angle+h/2, middle, middle_snapshot), (endpoint, fine, fine_snapshot)]
            self.rejections[cause] += 1
            failures += 1
            if failures >= 8:
                raise StopCalculation(f'8 rechazos consecutivos a {angle:.9f}°: {cause}, {worst}, E={error}')
            h *= .5 if cause == 'nonphysical' else step_factor(error, rejected=True)
            # Reducción real, no aceptar usando un mínimo impuesto tras el rechazo.

    def statistics(self):
        return dict(attempts=self.attempts, accepted_steps=self.accepted,
                    rejected_steps=sum(self.rejections.values()), rejections_by_cause=self.rejections,
                    rhs_evaluations=self.rhs_count, actual_substep_deg=dict(
                        minimum=self.minimum if self.accepted else None,
                        maximum=self.maximum if self.accepted else None,
                        mean=self.total/self.accepted if self.accepted else None),
                    rk_stage_evaluations=self.stage_evaluations,
                    endpoint_evaluations=self.endpoint_evaluations)


def run_adaptive(profile, monitor, model=None, trace=lambda row: None):
    started = time.monotonic()
    model = model or Model()
    layout = model.layout
    physical, size, ci = layout.physical, layout.size, layout.cylinder
    stepper = Stepper(model, profile, trace)
    y, angle, heat = model.initial_state(), model.case.initial_angle_deg, None
    cycles, recent, previous_curve = [], deque(maxlen=2), []
    streak, converged = 0, False
    stop, partial = 'límite de 30 ciclos, no convergido', None
    rows = []
    try:
        for cycle in range(1, 31):
            begin, end = angle, angle+layout.period
            start = y[:physical]
            y = start+[0.]*(size-physical)
            independent = [0.]*size
            snapshot = stepper.evaluate(angle, y, heat)[1]
            rows = [sample(angle, y, snapshot, rpm=model.case.rpm, initial_angle=model.case.initial_angle_deg, layout=layout)]
            pmax, fs = snapshot[0][ci][0], 0.
            for event in targets(begin, end, model.events, layout.period):
                while angle < event:
                    if angle == model.case.heat_start_deg+layout.period*math.floor((angle-model.case.heat_start_deg)/layout.period):
                        heat = (angle, y[3*ci+2])
                        fs = y[3*ci+2]
                    if heat is not None and angle >= heat[0]+model.case.heat_duration_deg:
                        heat = None
                    def check():
                        monitor(cycle, angle, stepper.rhs_count)
                    accepted = stepper.advance(angle, y, event, heat, check)
                    for next_angle, candidate, next_snapshot in accepted:
                        dt = (next_angle-angle)/model.rate
                        db = candidate[layout.burn]-y[layout.burn]
                        inc = independent_increment(snapshot, next_snapshot, dt,
                                                    model.case.fresh_energy_j_kg*db, db, layout)
                        independent = [a+b for a, b in zip(independent, inc)]
                        y, angle, snapshot = candidate, next_angle, next_snapshot
                        pmax = max(pmax, snapshot[0][ci][0])
                        if (angle-begin)*2 == round((angle-begin)*2):
                            rows.append(sample(angle, y, snapshot, rpm=model.case.rpm, initial_angle=model.case.initial_angle_deg, layout=layout))
            discrete, independent_balance = audit(start, y, y, layout), audit(start, y, independent, layout)
            summary = dict(cycle=cycle, state=y[:physical], Y=[n[2] for n in snapshot[0]],
                           W_C_J=y[layout.work+ci], p_max_Pa=pmax,
                           F_s_kg=fs, Q_J=y[layout.heat], converted_kg=y[layout.burn],
                           net_link_mass_kg=[y[physical+3*j] for j in range(len(layout.ends))],
                           discrete=discrete, independent=independent_balance,
                           balances_passed=balances_ok(discrete, independent_balance))
            if 'K' in layout.cv:
                summary['W_K_J'] = y[layout.work+layout.cv.index('K')]
            curve = [r['p_T_Y'][ci][0] for r in rows]
            if len(curve) != 2*layout.period+1:
                raise StopCalculation(f'salida común incompleta: {len(curve)} nodos')
            summary['convergence'] = convergence(cycles[-1] if cycles else None, summary, previous_curve, curve)
            streak = streak+1 if cycle >= 5 and summary['convergence']['passed'] else 0
            cycles.append(summary)
            recent.append(rows)
            previous_curve = curve
            monitor(cycle, angle, stepper.rhs_count, completed=True)
            if streak >= 3:
                stop, converged = 'convergencia: tres ciclos consecutivos', True
                break
    except StopCalculation as exc:
        stop = str(exc)
        partial = dict(angle_deg=angle, state=y[:physical], ledger=y[physical:], samples=rows,
                       W_C_J=y[layout.work+ci], p_max_Pa=pmax,
                       Y=[n[2] for n in snapshot[0]],
                       discrete=audit(start, y, y, layout), independent=audit(start, y, independent, layout))
        if 'K' in layout.cv:
            partial['W_K_J'] = y[layout.work+layout.cv.index('K')]
    return dict(profile=asdict(profile), step_deg=profile.max_step_deg, cycles=cycles,
                controller=dict(estimator_divisor=15, safety=.9, exponent=.2,
                                factor_bounds=[.2, 2.], minimum_substep_deg=MIN_SUBSTEP,
                                accepted_trajectory='two half steps', extrapolation=False),
                last_two_cycles=list(recent), partial=partial, stop=stop, converged=converged,
                seconds=time.monotonic()-started, final_angle_deg=angle, **stepper.statistics())
