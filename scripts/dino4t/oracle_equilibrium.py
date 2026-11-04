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
    return out

if __name__ == "__main__":
    json.dump(cases(), open(sys.argv[1], "w"), indent=1)
