"""NASA 7-coefficient species records with verbatim provenance.

Records are copied byte-for-byte (fixed-width CHEMKIN-II format) from the
primary sources below and parsed at import time, so transcription can be
audited against the source files by their SHA-256.

Sources (accessed 2026-11-04):

* GRI-Mech 3.0 thermodynamic data, ``thermo30.dat``
  http://combustion.berkeley.edu/gri-mech/version30/files30/thermo30.dat
  SHA-256 of the downloaded file:
  8d918b771aa965fe05e8c8f1f7e926a5326ebc90e7fc923ce129dc118b634dcc
* A. Burcat, B. Ruscic et al., Extended Third Millennium Thermodynamic
  Database for Combustion and Air-Pollution Use (``BURCAT.THR``)
  https://respecth.elte.hu/burcat/BURCAT.THR
  SHA-256 of the downloaded file:
  42a597ff852d1a2995f81d4fdca069f3cdcaef77ead5e3c66e02e80ed6699101
  Record ``C8H18,isooctane P 4/85`` (2,2,4-trimethylpentane, CAS 540-84-1,
  HF298 = -224.01 kJ/mol).

Burcat line 4 carries an extra H(298)/R field after a7(low); it is not a
polynomial coefficient and is ignored by the parser.
"""
from __future__ import annotations

GRI30_SHA256 = "8d918b771aa965fe05e8c8f1f7e926a5326ebc90e7fc923ce129dc118b634dcc"
BURCAT_SHA256 = "42a597ff852d1a2995f81d4fdca069f3cdcaef77ead5e3c66e02e80ed6699101"
ACCESSED = "2026-11-04"

GRI30 = "GRI-Mech 3.0 thermo30.dat"
BURCAT = "Burcat-Ruscic BURCAT.THR"

# name -> (source, elements, verbatim lines 1-4)
RECORDS = {
    "IC8H18": (BURCAT, {"C": 8, "H": 18}, """\
C8H18,isooctane   P 4/85C  8.H 18.   0.   0.G   200.000  6000.000  C 114.22852 1
 1.76160941E+01 5.13323108E-02-1.65307266E-05 2.43232275E-09-1.35572757E-13    2
-3.63461118E+04-6.86446285E+01 8.15741071E-01 7.32647307E-02 1.78301503E-05    3
-6.93592790E-08 3.21630852E-11-3.04774255E+04 2.41511097E+01-2.69420567E+04    4
"""),
    "O2": (GRI30, {"O": 2}, """\
O2                TPIS89O   2               G   200.000  3500.000  1000.000    1
 3.28253784E+00 1.48308754E-03-7.57966669E-07 2.09470555E-10-2.16717794E-14    2
-1.08845772E+03 5.45323129E+00 3.78245636E+00-2.99673416E-03 9.84730201E-06    3
-9.68129509E-09 3.24372837E-12-1.06394356E+03 3.65767573E+00                   4
"""),
    "N2": (GRI30, {"N": 2}, """\
N2                121286N   2               G   300.000  5000.000  1000.000    1
 0.02926640E+02 0.14879768E-02-0.05684760E-05 0.10097038E-09-0.06753351E-13    2
-0.09227977E+04 0.05980528E+02 0.03298677E+02 0.14082404E-02-0.03963222E-04    3
 0.05641515E-07-0.02444854E-10-0.10208999E+04 0.03950372E+02                   4
"""),
    "AR": (GRI30, {"AR": 1}, """\
AR                120186AR  1               G   300.000  5000.000  1000.000    1
 0.02500000E+02 0.00000000E+00 0.00000000E+00 0.00000000E+00 0.00000000E+00    2
-0.07453750E+04 0.04366000E+02 0.02500000E+02 0.00000000E+00 0.00000000E+00    3
 0.00000000E+00 0.00000000E+00-0.07453750E+04 0.04366000E+02                   4
"""),
    "CO2": (GRI30, {"C": 1, "O": 2}, """\
CO2               L 7/88C   1O   2          G   200.000  3500.000  1000.000    1
 3.85746029E+00 4.41437026E-03-2.21481404E-06 5.23490188E-10-4.72084164E-14    2
-4.87591660E+04 2.27163806E+00 2.35677352E+00 8.98459677E-03-7.12356269E-06    3
 2.45919022E-09-1.43699548E-13-4.83719697E+04 9.90105222E+00                   4
"""),
    "H2O": (GRI30, {"H": 2, "O": 1}, """\
H2O               L 8/89H   2O   1          G   200.000  3500.000  1000.000    1
 3.03399249E+00 2.17691804E-03-1.64072518E-07-9.70419870E-11 1.68200992E-14    2
-3.00042971E+04 4.96677010E+00 4.19864056E+00-2.03643410E-03 6.52040211E-06    3
-5.48797062E-09 1.77197817E-12-3.02937267E+04-8.49032208E-01                   4
"""),
    "CO": (GRI30, {"C": 1, "O": 1}, """\
CO                TPIS79C   1O   1          G   200.000  3500.000  1000.000    1
 2.71518561E+00 2.06252743E-03-9.98825771E-07 2.30053008E-10-2.03647716E-14    2
-1.41518724E+04 7.81868772E+00 3.57953347E+00-6.10353680E-04 1.01681433E-06    3
 9.07005884E-10-9.04424499E-13-1.43440860E+04 3.50840928E+00                   4
"""),
    "H2": (GRI30, {"H": 2}, """\
H2                TPIS78H   2               G   200.000  3500.000  1000.000    1
 3.33727920E+00-4.94024731E-05 4.99456778E-07-1.79566394E-10 2.00255376E-14    2
-9.50158922E+02-3.20502331E+00 2.34433112E+00 7.98052075E-03-1.94781510E-05    3
 2.01572094E-08-7.37611761E-12-9.17935173E+02 6.83010238E-01                   4
"""),
}

# IUPAC conventional atomic weights, kg/kmol (same values as motorsim.fuel_library).
ATOMIC_WEIGHT = {"C": 12.011, "H": 1.008, "O": 15.999, "N": 14.007, "AR": 39.948}


def parse_nasa7(text: str) -> dict:
    """Parse one fixed-width CHEMKIN-II record; returns ranges and coefficients."""
    lines = text.splitlines()
    if len(lines) != 4 or not all(line.rstrip().endswith(str(k + 1)) for k, line in enumerate(lines)):
        raise ValueError("NASA7 record requires four numbered lines")
    head = lines[0]
    t_low, t_high = float(head[45:55]), float(head[55:65])
    try:
        t_mid = float(head[65:73])
    except ValueError:
        # Burcat headers store the molar mass here; their common T_mid is 1000 K.
        t_mid = 1000.0
    fields = []
    for line, count in ((lines[1], 5), (lines[2], 5), (lines[3], 4)):
        fields += [float(line[15 * k:15 * (k + 1)]) for k in range(count)]
    high, low = fields[0:7], fields[7:14]
    return {"t_low": t_low, "t_mid": t_mid, "t_high": t_high,
            "low": tuple(low), "high": tuple(high)}
