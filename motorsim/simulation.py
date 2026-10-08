"""Prototipo 0D fijo. SI, RK4 explícito, sin Qt ni persistencia de proyectos."""
from bisect import bisect_right
from dataclasses import dataclass
from collections import deque
import math
import time

from .ducts import route_geometry
from .intake import intake_results
from .kinematics import piston_position
from .ports import crossing_angle, uncovered_area
from .simulation_case import SyntheticCase

CV = ('I', 'K', 'C', 'E')
# None representa un reservorio; no hay enlaces con almacenamiento propio.
ENDS = ((None, 0), (0, 1), (1, 2), (1, 2), (2, 3), (3, None))
SIZE, WORK, HEAT, BURN, ABS_M, ABS_H = 48, 30, 34, 35, 36, 42


@dataclass(frozen=True)
class Layout:
    cv: tuple = CV
    ends: tuple = ENDS
    cylinder: int = 2
    period: int = 360

    @property
    def physical(self): return 3*len(self.cv)
    @property
    def work(self): return self.physical+3*len(self.ends)
    @property
    def heat(self): return self.work+len(self.cv)
    @property
    def burn(self): return self.heat+1
    @property
    def abs_m(self): return self.burn+1
    @property
    def abs_h(self): return self.abs_m+len(self.ends)
    @property
    def size(self): return self.abs_h+len(self.ends)


TWO_LAYOUT = Layout()
FOUR_LAYOUT = Layout(('I', 'C', 'E'), ((None, 0), (0, 1), (1, 2), (2, None)), 1, 720)


class StopCalculation(RuntimeError):
    pass


class InvalidStage(ValueError):
    pass


def restriction(left, right, area, cd, gas_r=287, gamma=1.35, *, stable=False):
    """Una evaluación: (masa, entalpía, fresca)/s, signo izquierda→derecha.

    Extremos (p absoluta, T, Y). El donante cambia para las tres magnitudes.
    """
    if area == 0 or left[0] == right[0]:
        return (0.0, 0.0, 0.0)
    sign = 1 if left[0] > right[0] else -1
    donor, receiver = (left, right) if sign == 1 else (right, left)
    p, temperature, fresh = donor
    beta = receiver[0] / p
    critical = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    if beta <= critical:
        phi = math.sqrt(gamma) * (2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1)))
    elif stable:
        log_beta = math.log1p((receiver[0]-p)/p)
        phi = math.sqrt(2 * gamma / (gamma - 1) * math.exp(2/gamma*log_beta)
                        * -math.expm1((gamma-1)/gamma*log_beta))
    else:
        phi = math.sqrt(2 * gamma / (gamma - 1) *
                        (beta ** (2 / gamma) - beta ** ((gamma + 1) / gamma)))
    mass = sign * cd * area * p / math.sqrt(gas_r * temperature) * phi
    return mass, mass * (gamma * gas_r / (gamma - 1)) * temperature, mass * fresh


def regularized_restriction(left, right, area, cd, delta_p, gas_r=287, gamma=1.35):
    """Variante candidata exterior; banda fija en Pa, no calibración física."""
    if delta_p not in (50, 100):
        raise ValueError('Solo bandas autorizadas de 50 o 100 Pa.')
    z = abs(left[0]-right[0])/delta_p
    if z >= 1:
        return restriction(left, right, area, cd, gas_r, gamma)
    flow = restriction(left, right, area, cd, gas_r, gamma, stable=True)
    factor = math.sqrt(z)*(1.5-.5*z)
    return tuple(value*factor for value in flow)


def add_transport(derivative, left, right, transport):
    """Conserva exactamente el mismo transporte con signos opuestos."""
    for node, sign in ((left, -1), (right, 1)):
        if node is not None:
            for component in range(3):
                derivative[3 * node + component] += sign * transport[component]


def burn_fraction(angle, start, duration=40):
    z = (angle - start) / duration
    if z <= 0:
        return 0.0
    if z >= 1:
        return 1.0
    return z - math.sin(2 * math.pi * z) / (2 * math.pi)


def burn_rate(angle, start, duration=40):
    z = (angle - start) / duration
    return (1 - math.cos(2 * math.pi * z)) / duration if 0 < z < 1 else 0.0


def rk4(t, state, dt, rhs, project=lambda t, y: y):
    """RK4 en segundos; project aplica la solución analítica en cada etapa."""
    y = project(t, state)
    k1 = rhs(t, y)
    k2 = rhs(t + dt / 2, project(t + dt / 2, [v + dt / 2 * k for v, k in zip(y, k1)]))
    k3 = rhs(t + dt / 2, project(t + dt / 2, [v + dt / 2 * k for v, k in zip(y, k2)]))
    k4 = rhs(t + dt, project(t + dt, [v + dt * k for v, k in zip(y, k3)]))
    return project(t + dt, [v + dt / 6 * (a + 2*b + 2*c + d)
                            for v, a, b, c, d in zip(y, k1, k2, k3, k4)])


class Model:
    layout = TWO_LAYOUT
    def __init__(self, case=None, *, external_band_pa=None):
        if external_band_pa not in (None, 50, 100):
            raise ValueError('Solo ley original o bandas de 50/100 Pa.')
        self.external_band_pa = external_band_pa
        self.case = case or SyntheticCase()
        p = self.case.project_geometry
        p.validate()
        self.rate = 6 * self.case.rpm
        self.cv = self.case.gas_r / (self.case.gamma - 1)
        self.ap = math.pi * (p.bore_mm * .001) ** 2 / 4
        self.clearance = self.ap * p.stroke_mm * .001 / (p.compression_ratio - 1)
        self.duct_volumes, self.throats = [], []
        for route in (p.ducts.intake, p.ducts.exhaust):
            g = route_geometry(route)
            if g.errors or not all(g.joints):
                raise ValueError('El caso requiere conductos completos y continuos.')
            self.duct_volumes.append(float(g.volume) * 1e-6)
            self.throats.append(float(min(min(s.start_area, s.end_area) for s in g.segments)) * 1e-6)
        intake = intake_results(p.intake, p.stroke_mm, p.rod_length_mm)
        if intake.event_error or intake.area_error or intake.never_opens:
            raise ValueError('Admisión incompatible con el caso encendido.')
        self.intake_distance = p.intake.top_mm + p.intake.height_mm - p.intake.skirt_mm
        phases = {0., 180., self.case.heat_start_deg,
                  (self.case.heat_start_deg + self.case.heat_duration_deg) % 360,
                  intake.opening, intake.closing}
        for port in p.ports:
            for distance in (port.top_mm, port.top_mm + port.height_mm):
                if 0 < distance < p.stroke_mm:
                    beta = crossing_angle(p.stroke_mm, p.rod_length_mm, distance)
                    phases.update((beta, 360 - beta))
        d = self.intake_distance - p.intake.height_mm
        if 0 < d < p.stroke_mm:
            beta = crossing_angle(p.stroke_mm, p.rod_length_mm, d)
            phases.update((beta, 360 - beta))
        self.events = sorted(phases)

    def geometry(self, angle):
        p = self.case.project_geometry
        x = piston_position(p.stroke_mm, p.rod_length_mm, angle)
        theta = math.radians(angle % 360)
        r, rod = p.stroke_mm * .0005, p.rod_length_mm * .001
        sine, cosine = math.sin(theta), math.cos(theta)
        dx = r*sine + r*r*sine*cosine / math.sqrt(rod*rod - r*r*sine*sine)
        dv = self.ap * dx * self.rate * math.pi / 180
        volumes = (self.duct_volumes[0],
                   p.crankcase_volume_bdc_cm3 * 1e-6 + self.ap * (p.stroke_mm-x) * .001,
                   self.clearance + self.ap*x*.001, self.duct_volumes[1])
        ports = [uncovered_area(port.width_mm, port.height_mm, x-port.top_mm) * 1e-6
                 for port in p.ports]
        ai = uncovered_area(p.intake.width_mm, p.intake.height_mm, self.intake_distance-x) * 1e-6
        return volumes, (0., -dv, dv, 0.), (self.throats[0], ai, ports[1], ports[2], ports[0], self.throats[1])

    def initial_state(self):
        volumes = self.geometry(self.case.initial_angle_deg)[0]
        y = []
        for (pressure, temperature, fresh), volume in zip(self.case.initial_pty, volumes):
            mass = pressure*volume / (self.case.gas_r*temperature)
            y.extend((mass, mass*self.cv*temperature, mass*fresh))
        return y + [0.] * (self.layout.size-self.layout.physical)

    def analytic(self, angle, y, heat):
        if heat is None:
            return y
        start, fresh = heat
        result = y.copy()
        result[3*self.layout.cylinder+2] = fresh * (1-burn_fraction(angle, start, self.case.heat_duration_deg))
        return result

    def evaluate(self, angle, y, heat=None):
        layout = self.layout
        volumes, dvs, areas = self.geometry(angle)
        nodes = []
        for i, volume in enumerate(volumes):
            mass, energy, fresh = y[3*i:3*i+3]
            where = f'{layout.cv[i]} a {angle:.9f} grados'
            if not all(math.isfinite(v) for v in (mass, energy, fresh, volume)) or min(mass, energy, volume) <= 0:
                raise InvalidStage(f'{where}: masa/energía/volumen no positivo o no finito')
            if not 0 <= fresh <= mass:
                raise InvalidStage(f'{where}: F fuera de [0,m]: F={fresh}, m={mass}')
            temperature = energy / (mass*self.cv)
            pressure = mass*self.case.gas_r*temperature/volume
            if not (100 <= temperature <= 4000 and 1000 <= pressure <= 2e7):
                raise StopCalculation(f'{where}: fuera del dominio T={temperature} K, p={pressure} Pa')
            nodes.append((pressure, temperature, fresh/mass))
        endpoints = tuple((self.case.reservoirs_pty[0] if left is None else nodes[left],
                           self.case.reservoirs_pty[1] if right is None else nodes[right])
                          for left, right in layout.ends)
        dy = [0.] * layout.size
        flows = []
        for j, ((left, right), area, cd, ends) in enumerate(zip(endpoints, areas, self.case.discharge_coefficients, layout.ends)):
            if j in (0, len(layout.ends)-1) and self.external_band_pa is not None:
                transport = regularized_restriction(left, right, area, cd, self.external_band_pa,
                                                   self.case.gas_r, self.case.gamma)
            else:
                transport = restriction(left, right, area, cd, self.case.gas_r, self.case.gamma)
            flows.append(transport)
            add_transport(dy, *ends, transport)
            dy[layout.physical+3*j:layout.physical+3*j+3] = transport
            dy[layout.abs_m+j], dy[layout.abs_h+j] = abs(transport[0]), abs(transport[1])
        for i in range(len(layout.cv)):
            dy[layout.work+i] = nodes[i][0]*dvs[i]
            dy[3*i+1] -= dy[layout.work+i]
        if heat is not None:
            start, fresh = heat
            if any(areas[j] for j, ends in enumerate(layout.ends) if layout.cylinder in ends):
                raise StopCalculation('Ventanas del cilindro abiertas durante aporte cerrado')
            dy[layout.burn] = fresh * burn_rate(angle, start, self.case.heat_duration_deg) * self.rate
            dy[layout.heat] = self.case.fresh_energy_j_kg * dy[layout.burn]
            dy[3*layout.cylinder+1] += dy[layout.heat]
            # F_C se evalúa analíticamente, incluida cada etapa RK4.
            dy[3*layout.cylinder+2] = 0.
        return dy, (nodes, volumes, flows)


def independent_increment(left, right, dt, q_exact, b_exact, layout=TWO_LAYOUT):
    """Trapecios en extremos aceptados, no pesos/etapas RK ni diferencias de estado.

    Flujo evaluado en salida refinada de cada paso. Trabajo = p_media * Delta V.
    Fuente prescrita integrada por su primitiva, independientemente del RK4 de U.
    """
    result = [0.] * layout.size
    ln, lv, lf = left
    rn, rv, rf = right
    for j, (a, b) in enumerate(zip(lf, rf)):
        for k in range(3):
            result[layout.physical+3*j+k] = dt * (a[k]+b[k]) / 2
        result[layout.abs_m+j] = dt*(abs(a[0])+abs(b[0]))/2
        result[layout.abs_h+j] = dt*(abs(a[1])+abs(b[1]))/2
    for i in range(len(layout.cv)):
        result[layout.work+i] = (ln[i][0]+rn[i][0]) / 2 * (rv[i]-lv[i])
    result[layout.heat], result[layout.burn] = q_exact, b_exact
    return result


def audit(start, end, ledger, layout=TWO_LAYOUT):
    """Balances por inventarios y libro de enlaces; global usa solo contornos."""
    records = {}
    for key, members in [*((name, (i,)) for i, name in enumerate(layout.cv)), ('global', tuple(range(len(layout.cv))))]:
        transfer = [0., 0., 0.]
        abs_mass = abs_h = 0.
        for j, (left, right) in enumerate(layout.ends):
            sign = int(right in members) - int(left in members)
            if sign:
                for k in range(3):
                    transfer[k] += sign * ledger[layout.physical+3*j+k]
                abs_mass += ledger[layout.abs_m+j]
                abs_h += ledger[layout.abs_h+j]
        work = sum(ledger[layout.work+i] for i in members)
        q = ledger[layout.heat] if layout.cylinder in members else 0.
        burnt = ledger[layout.burn] if layout.cylinder in members else 0.
        delta = [sum(end[3*i+k]-start[3*i+k] for i in members) for k in range(3)]
        residual = (delta[0]-transfer[0], delta[1]-(transfer[1]+q-work), delta[2]-(transfer[2]-burnt))
        mass_scale = max(sum(start[3*i] for i in members), abs_mass, 1e-9)
        energy_scale = max(sum(start[3*i+1] for i in members),
                           abs_h+abs(q)+sum(abs(ledger[layout.work+i]) for i in members), 1.)
        normalized = [abs(residual[0])/mass_scale, abs(residual[1])/energy_scale, abs(residual[2])/mass_scale]
        records[key] = dict(residual_kg_j_kg=list(residual), normalized_m_u_f=normalized)
    return records


def balances_ok(discrete, independent):
    return (all(r['normalized_m_u_f'][0] <= 1e-6 and r['normalized_m_u_f'][1] <= 1e-5
                and r['normalized_m_u_f'][2] <= 1e-6 for r in discrete.values())
            and all(max(r['normalized_m_u_f']) <= .001 for r in independent.values()))


def convergence(previous, current, previous_curve, curve):
    if previous is None:
        return {'passed': False}
    m = max(abs(current['state'][3*i]-previous['state'][3*i]) /
            max(abs(current['state'][3*i]), abs(previous['state'][3*i]), 1e-9) for i in range(len(current["Y"])))
    u = max(abs(current['state'][3*i+1]-previous['state'][3*i+1]) /
            max(abs(current['state'][3*i+1]), abs(previous['state'][3*i+1]), 1.) for i in range(len(current["Y"])))
    fresh = max(abs(a-b) for a, b in zip(current['Y'], previous['Y']))
    work = abs(current['W_C_J']-previous['W_C_J'])/max(abs(current['W_C_J']), abs(previous['W_C_J']), 1.)
    pressure = max(abs(a-b) for a, b in zip(curve, previous_curve))/max(current['p_max_Pa'], previous['p_max_Pa'], 100000.)
    passed = (m <= .002 and u <= .002 and fresh <= .002 and work <= .005 and pressure <= .005
              and current['balances_passed'] and current['F_s_kg'] > 0 and current['Q_J'] > 0)
    return dict(m_relative=m, U_relative=u, Y_absolute=fresh, W_relative=work,
                p_curve_relative=pressure, passed=passed)


def sample(angle, y, snapshot, *, rpm=3000, initial_angle=180, layout=TWO_LAYOUT):
    nodes, volumes, flows = snapshot
    result = dict(angle_deg=angle, time_s=(angle-initial_angle)/(6*rpm), state=y[:layout.physical],
                  p_T_Y=nodes, V_m3=volumes, flows_kg_s_W_kg_s=flows,
                  W_C_J=y[layout.work+layout.cylinder], Q_J=y[layout.heat], converted_kg=y[layout.burn])
    if 'K' in layout.cv:
        result['W_K_J'] = y[layout.work+layout.cv.index('K')]
    return result


def run_resolution(step_deg, monitor, model=None):
    """Una ejecución desde el arranque fijado; monitor verifica presupuestos/cancelación."""
    model = model or Model()
    started = time.monotonic()
    y = model.initial_state()
    angle = model.case.initial_angle_deg
    heat = None
    cycles, recent = [], deque(maxlen=2)
    previous_curve = []
    rhs_count = accepted = rejected = consecutive = 0
    stop = 'límite de 30 ciclos, no convergido'
    converged = False
    current_samples = []
    partial = None
    try:
        for cycle in range(1, 31):
            begin = angle
            end = begin + 360
            start = y[:12]
            y = start + [0.] * (SIZE-12)
            independent = [0.] * SIZE
            _, snapshot = model.evaluate(angle, y, heat)
            current_samples = [sample(angle, y, snapshot, rpm=model.case.rpm, initial_angle=model.case.initial_angle_deg)]
            max_pressure = snapshot[0][2][0]
            fresh_start = 0.
            events = sorted({begin+i*.5 for i in range(1, 721)} |
                            {turn*360+phase for turn in range(int(begin//360), int(end//360)+1)
                             for phase in model.events if begin < turn*360+phase <= end})
            while angle < end:
                monitor(cycle, angle, rhs_count)
                event = events[bisect_right(events, angle)]
                target = min(angle+step_deg, event, end)
                heat_start = 350 + 360*math.floor((angle-350)/360)
                if angle == heat_start:
                    heat = (angle, y[8])
                    fresh_start = y[8]
                if heat is not None and angle >= heat[0]+model.case.heat_duration_deg:
                    heat = None
                failures = 0
                while True:
                    dt = (target-angle)/model.rate
                    def rhs(t, stage):
                        nonlocal rhs_count
                        if rhs_count >= 2_000_000:
                            raise StopCalculation('límite de 2000000 evaluaciones RHS')
                        rhs_count += 1
                        return model.evaluate(angle+t*model.rate, stage, heat)[0]
                    def project(t, stage):
                        return model.analytic(angle+t*model.rate, stage, heat)
                    try:
                        candidate = rk4(0., y, dt, rhs, project)
                        # Conversión acumulada por primitiva, no integral RK4.
                        b_exact = (heat[1]*(burn_fraction(target, heat[0])-burn_fraction(angle, heat[0]))
                                   if heat else 0.)
                        candidate[BURN] = y[BURN]+b_exact
                        _, next_snapshot = model.evaluate(target, candidate, heat)
                        break
                    except InvalidStage as exc:
                        rejected += 1
                        failures += 1
                        if failures >= 8 or (target-angle)/2 < .001:
                            raise StopCalculation(f'rechazo/paso mínimo: {exc}') from exc
                        target = angle+(target-angle)/2
                        monitor(cycle, angle, rhs_count)
                inc = independent_increment(snapshot, next_snapshot, dt,
                                            model.case.fresh_energy_j_kg*b_exact, b_exact)
                independent = [a+b for a, b in zip(independent, inc)]
                y, angle, snapshot = candidate, target, next_snapshot
                accepted += 1
                max_pressure = max(max_pressure, snapshot[0][2][0])
                if (angle-begin)*2 == round((angle-begin)*2):
                    current_samples.append(sample(angle, y, snapshot, rpm=model.case.rpm, initial_angle=model.case.initial_angle_deg))
            discrete = audit(start, y, y)
            independent_balance = audit(start, y, independent)
            summary = dict(cycle=cycle, state=y[:12], Y=[n[2] for n in snapshot[0]],
                           W_C_J=y[WORK+2], W_K_J=y[WORK+1], p_max_Pa=max_pressure,
                           F_s_kg=fresh_start, Q_J=y[HEAT], converted_kg=y[BURN],
                           net_link_mass_kg=[y[12+3*j] for j in range(6)],
                           discrete=discrete, independent=independent_balance,
                           balances_passed=balances_ok(discrete, independent_balance))
            curve = [row['p_T_Y'][2][0] for row in current_samples]
            if len(curve) != 721:
                raise StopCalculation(f'salida común incompleta: {len(curve)} nodos')
            summary['convergence'] = convergence(cycles[-1] if cycles else None, summary, previous_curve, curve)
            consecutive = consecutive+1 if cycle >= 5 and summary['convergence']['passed'] else 0
            cycles.append(summary)
            recent.append(current_samples)
            previous_curve = curve
            monitor(cycle, angle, rhs_count, completed=True)
            if consecutive >= 3:
                stop, converged = 'convergencia: tres ciclos consecutivos', True
                break
    except StopCalculation as exc:
        stop = str(exc)
        partial = dict(angle_deg=angle, state=y[:12], samples=current_samples)
    return dict(step_deg=step_deg, cycles=cycles, last_two_cycles=list(recent),
                partial=partial, stop=stop, converged=converged, seconds=time.monotonic()-started,
                accepted_steps=accepted, rejected_steps=rejected, rhs_evaluations=rhs_count,
                final_angle_deg=angle)


def sensitivity(runs, cylinder=2):
    if len(runs) != 3 or not all(r['converged'] for r in runs):
        return dict(passed=False, reason='Requiere las tres resoluciones convergidas.')
    a, b, c = [r['cycles'][-1] for r in runs]
    ca, cb, cc = [[s['p_T_Y'][cylinder][0] for s in r['last_two_cycles'][-1]] for r in runs]
    coarse, fine = {}, {}
    for key, floor in (('W_C_J', 1.), ('p_max_Pa', c['p_max_Pa'])):
        scale = max(abs(c[key]), abs(b[key]), floor) if key == 'W_C_J' else floor
        fine[key] = abs(c[key]-b[key])/scale
        coarse[key] = abs(b[key]-a[key])/scale
    fine['curve'] = max(abs(x-y) for x, y in zip(cc, cb))/c['p_max_Pa']
    coarse['curve'] = max(abs(x-y) for x, y in zip(cb, ca))/c['p_max_Pa']
    fine['Y'] = [abs(x-y) for x, y in zip(c['Y'], b['Y'])]
    coarse['Y'] = [abs(x-y) for x, y in zip(b['Y'], a['Y'])]
    scales = [max(abs(x), abs(y), 1e-7) for x, y in zip(c['net_link_mass_kg'], b['net_link_mass_kg'])]
    fine['links'] = [abs(x-y)/s for x, y, s in zip(c['net_link_mass_kg'], b['net_link_mass_kg'], scales)]
    coarse['links'] = [abs(x-y)/s for x, y, s in zip(b['net_link_mass_kg'], a['net_link_mass_kg'], scales)]
    tolerances = (max(fine['W_C_J'], fine['p_max_Pa'], fine['curve'], *fine['links']) <= .01
                  and max(fine['Y']) <= .005)
    # Pisos ya fijados: 1 J y 1e-7 kg. No imponer tendencia a discrepancias
    # menores que esos pisos; p/Y no tienen un piso adicional aprobado.
    work_trend = (abs(c['W_C_J']-b['W_C_J']) <= 1.
                  or fine['W_C_J'] <= coarse['W_C_J'])
    link_trend = all(abs(x-y) <= 1e-7 or f <= g for x, y, f, g in zip(
        c['net_link_mass_kg'], b['net_link_mass_kg'], fine['links'], coarse['links']))
    trend = (work_trend and link_trend
             and all(fine[k] <= coarse[k] for k in ('p_max_Pa', 'curve'))
             and all(x <= y for x, y in zip(fine['Y'], coarse['Y'])))
    return dict(passed=tolerances and trend, fine=fine, coarse=coarse,
                tolerances_passed=tolerances, decreasing_discrepancy=trend)
