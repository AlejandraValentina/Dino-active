"""Candidato experimental; no importado por MotorSim ni activado por defecto.

Limita transferencias antes de construir estados. No recorta F ni modifica m/U.
Los casos sin solución mediante reducción de flujos se rechazan explícitamente.
"""
import math
from motorsim.simulation import InvalidStage, TWO_LAYOUT


class LimiterDiagnostics:
    def __init__(self, rpm=0, emit=lambda row: None):
        self.rpm, self.emit = rpm, emit
        self.activation_count = 0
        self.min_alpha = 1.
        self.total_corrected = self.max_correction = 0.
        self.infeasible = 0

    def record(self, original, limited, dt, angle, stage, layout):
        corrections = []
        for (j, q, f), (_, _, g) in zip(original, limited):
            if f != g:
                amount = dt*abs(f-g)
                alpha = abs(g/f) if f else 1.
                self.min_alpha = min(self.min_alpha, alpha)
                self.total_corrected += amount
                self.max_correction = max(self.max_correction, amount)
                corrections.append(dict(link=j, alpha=alpha, fresh_correction_kg=amount))
        if corrections:
            self.activation_count += 1
            self.emit(dict(rpm=self.rpm, angle_deg=angle,
                           cycle=int((angle-180)//360)+1, stage=stage, corrections=corrections))

    def metrics(self):
        return dict(limiter_activation_count=self.activation_count,
                    limiter_min_alpha=self.min_alpha,
                    limiter_total_corrected_fresh_kg=self.total_corrected,
                    limiter_max_single_correction_kg=self.max_correction,
                    limiter_infeasible_stages=self.infeasible,
                    includes_rejected_attempts=True)


def fresh_derivatives(transfers, layout):
    derivative = [0.]*len(layout.cv)
    ledger = [0.]*len(layout.ends)
    for j, q, f in transfers:
        left, right = layout.ends[j]
        if left is not None: derivative[left] -= f
        if right is not None: derivative[right] += f
        ledger[j] += f
    return derivative, ledger


def limit_stage_species_fluxes(base, candidate, transfers, dt, diagnostics,
                              *, angle=180., stage='', layout=TWO_LAYOUT):
    """Un flujo único por enlace/etapa, igual y opuesto entre sus extremos.

Solo factores [0,1]; un receptor puede limitar entradas. Si esto no tiene
solución no se fuerza F: se devuelve InvalidStage antes de evaluar el estado.
"""
    n = len(layout.cv)
    if all(0 <= candidate[3*i+2] <= candidate[3*i] for i in range(n)):
        return candidate, transfers
    original = transfers
    limited = list(transfers)
    for _ in range(64):
        incoming, outgoing = [0.]*n, [0.]*n
        donors, receivers = [], []
        for j, q, f in limited:
            left, right = layout.ends[j]
            donor, receiver = (left, right) if q >= 0 else (right, left)
            donors.append(donor); receivers.append(receiver)
            if donor is not None: outgoing[donor] += abs(f)
            if receiver is not None: incoming[receiver] += abs(f)
        factors = [1.]*len(limited)
        for i in range(n):
            low_budget = base[3*i+2]/dt + incoming[i]
            high_budget = (candidate[3*i]-base[3*i+2])/dt + outgoing[i]
            for budget, demand, endpoints in ((low_budget, outgoing[i], donors),
                                              (high_budget, incoming[i], receivers)):
                if demand > 0 and budget < demand:
                    alpha = max(0., math.nextafter(max(0., budget)/demand, 0.))
                    for k, node in enumerate(endpoints):
                        if node == i: factors[k] = min(factors[k], alpha)
        updated = [(j, q, f*a) for (j, q, f), a in zip(limited, factors)]
        derivatives, ledger = fresh_derivatives(updated, layout)
        result = candidate.copy()
        for i, value in enumerate(derivatives): result[3*i+2] = base[3*i+2]+dt*value
        for j, value in enumerate(ledger): result[layout.physical+3*j+2] = base[layout.physical+3*j+2]+dt*value
        if all(0 <= result[3*i+2] <= result[3*i] for i in range(n)):
            diagnostics.record(original, updated, dt, angle, stage, layout)
            return result, updated
        if updated == limited: break
        limited = updated
    diagnostics.record(original, limited, dt, angle, stage, layout)
    diagnostics.infeasible += 1
    raise InvalidStage('CONSERVATIVE_STAGE_SPECIES_LIMITER: sin solución representable por reducción de flujos')


def candidate_rk4(diagnostics, angle_at, layout=TWO_LAYOUT):
    """Mismos coeficientes y operaciones RK4 cuando no actúa el limiter."""
    def rk4(t, state, dt, rhs, project=lambda t, y: y):
        y = project(t, state)
        def form(k, length, time, label):
            candidate = [v+length*d for v, d in zip(y, k)]
            transfers = [(j, k[layout.physical+3*j], k[layout.physical+3*j+2])
                         for j in range(len(layout.ends))]
            candidate, limited = limit_stage_species_fluxes(y, candidate, transfers, length,
                diagnostics, angle=angle_at(time), stage=label, layout=layout)
            if limited is not transfers:
                derivatives, ledger = fresh_derivatives(limited, layout)
                k = k.copy()
                for i, value in enumerate(derivatives): k[3*i+2] = value
                for j, value in enumerate(ledger): k[layout.physical+3*j+2] = value
            return k, project(time, candidate)
        k1 = rhs(t, y)
        k1, s2 = form(k1, dt/2, t+dt/2, 'k2')
        k2 = rhs(t+dt/2, s2)
        k2, s3 = form(k2, dt/2, t+dt/2, 'k3')
        k3 = rhs(t+dt/2, s3)
        k3, s4 = form(k3, dt, t+dt, 'k4')
        k4 = rhs(t+dt, s4)
        result = [v+dt/6*(a+2*b+2*c+d) for v,a,b,c,d in zip(y,k1,k2,k3,k4)]
        transfers = [(j, weight*k[layout.physical+3*j], weight*k[layout.physical+3*j+2])
                     for k,weight in ((k1,1),(k2,2),(k3,2),(k4,1)) for j in range(len(layout.ends))]
        result, _ = limit_stage_species_fluxes(y, result, transfers, dt/6, diagnostics,
                                              angle=angle_at(t+dt), stage='final', layout=layout)
        return project(t+dt, result)
    return rk4
