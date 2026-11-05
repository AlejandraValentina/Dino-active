"""Stage-2 oracle: chemical-equilibrium reference values from Cantera (NOT a project dependency).

Run with a Python that has Cantera:  python oracle_equilibrium.py OUT.json
Uses the SAME NASA-7 records as Dino 4T (so thermodynamic data are shared and only the
equilibrium solver / energy bookkeeping are independent), plus the dissociation species.
"""
import importlib.util, json, sys
import numpy as np
import cantera as ct

here = __file__.replace("\\", "/").rsplit("/scripts/", 1)[0]
spec = importlib.util.spec_from_file_location("thermo_data", here + "/motorsim/dino4t/thermo_data.py")
td = importlib.util.module_from_spec(spec); spec.loader.exec_module(td)

def species(names):
    out = []
    for n in names:
        src, elements, text = td.RECORDS[n]
        r = td.parse_nasa7(text)
        coeffs = [r["t_mid"]] + list(r["high"]) + list(r["low"])
        sp = ct.Species(n, {k.capitalize() if k != "AR" else "Ar": v for k, v in elements.items()})
        sp.thermo = ct.NasaPoly2(r["t_low"], r["t_high"], 101325.0, coeffs)
        out.append(sp)
    return out

BASE = ["IC8H18", "O2", "N2", "AR", "CO2", "H2O", "CO", "H2"]
FULL = BASE + ["H", "O", "OH", "NO"]
PROD10 = ["O2", "N2", "AR", "CO2", "H2O", "CO", "H2", "H", "O", "OH"]
CHARGE10 = ["IC8H18"] + PROD10  # Dino 4T TWO_ZONE_EQUILIBRIUM_V1 species (NO excluded: kinetically controlled)
AIR = {"N2": 0.78084, "O2": 0.20946, "AR": 0.00934}

def gas(names):
    return ct.Solution(thermo="ideal-gas", species=species(names))

def charge_Y(g, phi):
    # stoichiometric moles O2 per mole isooctane = 12.5
    X = {k: v for k, v in AIR.items()}
    n_air = 12.5 / AIR["O2"] / phi
    comp = {"IC8H18": 1.0, **{k: v * n_air for k, v in AIR.items()}}
    g.X = comp
    return g.Y.copy()

def cases():
    out = {"cantera_version": ct.__version__, "thermo_sha256": {"gri30": td.GRI30_SHA256, "burcat": td.BURCAT_SHA256}, "cases": []}
    for phi in (0.6, 0.8, 1.0, 1.2):
        for label, T0, P0 in (("TDC_like", 700.0, 22e5), ("intake_like", 300.0, 1e5)):
            for names_label, names in (("full12", FULL), ("base8", BASE)):
                g = gas(names)
                Y = charge_Y(g, phi)
                g.TPY = T0, P0, Y
                u0 = g.int_energy_mass; v0 = g.volume_mass
                g.equilibrate("UV")
                out["cases"].append(dict(kind="UV", phi=phi, T0=T0, p0=P0, species_set=names_label,
                                         T_final=g.T, p_final=g.P, Y={n: float(g.Y[g.species_index(n)]) for n in names},
                                         u0=u0, v0=v0))
    # constant-pressure adiabatic flame temperature, isooctane/air, 298.15 K, 1 atm
    for phi in (0.8, 1.0, 1.2):
        g = gas(FULL); Y = charge_Y(g, phi); g.TPY = 298.15, 101325.0, Y; g.equilibrate("HP")
        out["cases"].append(dict(kind="HP", phi=phi, T0=298.15, p0=101325.0, species_set="full12", T_final=g.T,
                                 p_final=g.P, Y={n: float(g.Y[g.species_index(n)]) for n in FULL}))
    # equilibrium state grid for validating the Dino solver itself (T,P) with fixed elements
    grid = []
    for phi in (0.8, 1.0, 1.2):
        g = gas(FULL); Y = charge_Y(g, phi)
        for T in (1800.0, 2200.0, 2600.0, 3000.0):
            for P in (1e5, 20e5, 60e5):
                g.TPY = T, P, Y; g.equilibrate("TP")
                grid.append(dict(phi=phi, T=T, p=P, Y={n: float(g.Y[g.species_index(n)]) for n in FULL}, h=g.enthalpy_mass))
    out["tp_grid"] = grid
    # same grid, Dino 4T equilibrium species set (10 products, no NO)
    grid10 = []
    for phi in (0.8, 1.0, 1.2):
        g = gas(CHARGE10); Y = charge_Y(g, phi)
        for T in (1800.0, 2200.0, 2600.0, 3000.0):
            for P in (1e5, 20e5, 60e5):
                g.TPY = T, P, Y; g.equilibrate("TP")
                grid10.append(dict(phi=phi, T=T, p=P, Y={n: float(g.Y[g.species_index(n)]) for n in PROD10}, h=g.enthalpy_mass))
    out["tp_grid_prod10"] = grid10
    # UV explosions with the 10-species set
    uv10 = []
    for phi in (0.6, 0.8, 1.0, 1.2):
        for T0, P0 in ((700.0, 22e5), (300.0, 1e5)):
            g = gas(CHARGE10); Y = charge_Y(g, phi); g.TPY = T0, P0, Y; g.equilibrate("UV")
            uv10.append(dict(phi=phi, T0=T0, p0=P0, T_final=g.T, p_final=g.P))
    out["uv_prod10"] = uv10
    out["closure_cases"] = closure_cases()
    return out


def closure_cases():
    """Independent evaluation of the two-zone closure (isentropic frozen unburned zone + equilibrium
    burned zone, common pressure) with Cantera objects and scalar root finders."""
    from scipy.optimize import brentq
    res = []
    for phi in (0.8, 1.0):
        for T0, P0 in ((700.0, 22e5), (900.0, 60e5)):
            gu = gas(CHARGE10); gb = gas(CHARGE10)
            Y0 = charge_Y(gu, phi)
            gu.TPY = T0, P0, Y0
            u0, s0, v0 = gu.int_energy_mass, gu.entropy_mass, gu.volume_mass
            for x in (0.05, 0.25, 0.5, 0.75, 0.95, 1.0):
                def state_at(p):
                    if x < 1.0:
                        gu.Y = Y0; gu.SP = s0, p
                        Tu, eu, vu = gu.T, gu.int_energy_mass, gu.volume_mass
                    else:
                        Tu, eu, vu = 0.0, 0.0, 0.0
                    target = (u0 - (1 - x) * eu) / x
                    def eb(T):
                        gb.TPY = T, p, Y0; gb.equilibrate("TP"); return gb.int_energy_mass - target
                    if eb(500.0) * eb(5000.0) > 0:  # energy cannot be accommodated: pressure far too high
                        return Tu, float("nan"), 0.0
                    Tb = brentq(eb, 500.0, 5000.0, xtol=1e-10)
                    gb.TPY = Tb, p, Y0; gb.equilibrate("TP")
                    return Tu, Tb, (1 - x) * vu + x * gb.volume_mass
                gap = lambda lnp: state_at(np.exp(lnp))[2] - v0
                lnp = brentq(gap, np.log(P0), np.log(12 * P0), xtol=1e-13)
                Tu, Tb, _ = state_at(np.exp(lnp))
                res.append(dict(phi=phi, T0=T0, p0=P0, x_b=x, p=float(np.exp(lnp)), T_u=float(Tu), T_b=float(Tb),
                                u0=u0, s0=s0, v0=v0))
    return res


if __name__ == "__main__":
    json.dump(cases(), open(sys.argv[1], "w"), indent=1)
