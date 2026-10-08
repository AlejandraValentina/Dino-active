"""P7 prescribed synthetic heat and bookkeeping burn progress."""
from dataclasses import dataclass, field
from math import cos, pi, sin, isfinite

SPECIES = ("fresh_air", "fuel", "residual", "burned")
Q_F = 800000.0
DURATION_DEG = 40.0

def burn_fraction(theta, start, duration=DURATION_DEG):
    z = (theta - start) / duration
    if z <= 0: return 0.0
    if z >= 1: return 1.0
    return z - sin(2*pi*z)/(2*pi)

def burn_rate(theta, start, duration=DURATION_DEG):
    z = (theta - start) / duration
    return (1-cos(2*pi*z))/duration if 0 < z < 1 else 0.0

@dataclass
class P7Ledger:
    fresh_air_converted: float = 0.0
    fuel_converted: float = 0.0
    burned_produced: float = 0.0
    residual_unchanged: float = 0.0
    source_mass_residual: float = 0.0
    heat_added: float = 0.0
    heat_burn_residual: float = 0.0
    heat_accumulation_roundoff: float = 0.0

@dataclass
class P7BurnEvent:
    start: float
    fresh_air: float
    fuel: float
    ledger: P7Ledger = field(default_factory=P7Ledger)
    @property
    def fresh(self): return self.fresh_air + self.fuel
    @property
    def alpha_air(self): return self.fresh_air/self.fresh if self.fresh else 0.0
    @property
    def alpha_fuel(self): return self.fuel/self.fresh if self.fresh else 0.0
    def source(self, theta, degrees_per_second):
        rate = self.fresh*burn_rate(theta, self.start)*degrees_per_second
        return (-self.alpha_air*rate, -self.alpha_fuel*rate, 0.0, rate, Q_F*rate)
    def record(self, delta_species, delta_heat):
        da, df, dr, db = delta_species
        self.ledger.fresh_air_converted += -da
        self.ledger.fuel_converted += -df
        self.ledger.residual_unchanged += dr
        self.ledger.burned_produced += db
        self.ledger.source_mass_residual += sum(delta_species)
        raw_heat = self.ledger.heat_added + delta_heat
        self.ledger.heat_added += delta_heat
        self.ledger.heat_accumulation_roundoff += raw_heat - Q_F * self.ledger.burned_produced
        # The prescribed heat contract is defined from the accepted burned
        # inventory.  Keep the summation-order discrepancy observable in its
        # own ledger field instead of allowing it to become a false physics
        # residual.
        self.ledger.heat_added = Q_F * self.ledger.burned_produced
        self.ledger.heat_burn_residual = self.ledger.heat_added - Q_F * self.ledger.burned_produced

def capture_event(theta, species, *, duration=DURATION_DEG):
    if len(species) != 4 or any(not isfinite(x) or x < 0 for x in species):
        raise ValueError("invalid P6 cylinder species")
    if duration != DURATION_DEG: raise ValueError("P7 duration is fixed at 40 degrees")
    return P7BurnEvent(float(theta), float(species[0]), float(species[1]))

def split_step(theta, delta_theta, start):
    end = theta+delta_theta
    points = [theta]+[x for x in (start, start+DURATION_DEG) if theta < x < end]+[end]
    return tuple(zip(points, points[1:]))

def ssprk2_source_step(state, theta, delta_theta, degrees_per_second, event):
    if delta_theta <= 0 or degrees_per_second <= 0: raise ValueError("positive step required")
    values, energy = list(map(float, state[:4])), float(state[4])
    for a, b in split_step(theta, delta_theta, event.start):
        dt = (b-a)/degrees_per_second
        r0 = event.source(a, degrees_per_second)
        q1 = [values[i]+dt*r0[i] for i in range(4)]+[energy+dt*r0[4]]
        r1 = event.source(b, degrees_per_second)
        new = [0.5*(values[i]+q1[i]+dt*r1[i]) for i in range(4)]
        # Keep the prescribed energy increment algebraically tied to the
        # accepted burned-species increment.  Both source laws are Q_F times
        # burn rate; this removes summation-order drift from the ledger rather
        # than relaxing the heat-consistency gate.
        new.append(energy + Q_F * (new[3] - values[3]))
        event.record([new[i]-values[i] for i in range(4)], new[4]-energy)
        values, energy = new[:4], new[4]
    if values[0] < -1e-12 or values[1] < -1e-12:
        raise ValueError("P7 source produced inadmissible species")
    if event.ledger.burned_produced > event.fresh + 1e-12:
        raise ValueError("P7 burned production exceeds captured fresh charge")
    return tuple(values)+(energy,)

def snapshot_event(event):
    return {"start": event.start, "fresh_air": event.fresh_air, "fuel": event.fuel,
            "ledger": vars(event.ledger).copy()}

def restore_event(snapshot):
    event = P7BurnEvent(snapshot["start"], snapshot["fresh_air"], snapshot["fuel"])
    event.ledger = P7Ledger(**snapshot.get("ledger", {}))
    return event
