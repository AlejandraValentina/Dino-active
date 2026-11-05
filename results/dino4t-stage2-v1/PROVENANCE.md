# Procedencia de los resultados de `results/dino4t-stage2-v1`

Todo es **verificación numérica / estudio de ingeniería con parámetros sintéticos**. Nada es validación ni predicción.
Los resultados de la etapa 1 (`results/dino4t-foundation-v1/`) son **históricos** (contorno V1, defectuoso) y no deben usarse.

| Carpeta | Qué es | Código con el que se generó | Reproducción |
|---|---|---|---|
| `oracle/` | Referencias Cantera 3.2.0 (entorno aislado) | `scripts/dino4t/oracle_equilibrium.py` | ver docstring del script |
| `verification/` | Suite de aceptación (31 casos) | árbol de cierre de la etapa 2 (commit en `verification_report.json`) | `python -m motorsim.dino4t verify --out ...` |
| `example/{4000,6000,8000}rpm/` | Ejemplo sintético, V2 + dos zonas | commit de cierre; `summary.json` declara `code_commit`, `code_dirty` y `models` | `python -m motorsim.dino4t run configs/dino4t/example_single_cylinder_500cc.json --out ... --rpm N` |
| `robustness/` | Matrices de estrés (11 casos) | ver nota 1 | `scripts/dino4t/stress_matrix.py` |
| `studies/S2, S3, S4` | Barrido de longitud/RPM, fase de admisión, sensibilidades | ver nota 2 | `scripts/dino4t/run_stage2_studies.py` |
| `studies/S2b` | Barrido refinado (500 rpm) de H2 y control de malla | ver nota 2 | `scripts/dino4t/run_stage2_h2_refined.py` |
| `audit/` | Barrido de régimen de la frontera, Mach de cara en el motor, lista de fallos preexistentes del repositorio | ver nota 2 | `scripts/dino4t/audit_*.py` |

**Nota 1.** `stress_matrix_v2*.json` se generó con el árbol de trabajo sin commitear (sobre `1e7f2ca`);
`stress_matrix_v2_twozone_guarded.json` se regeneró con el código de cierre y la frontera con falla explícita para
comprobar que no cambia ningún caso.

**Nota 2.** S2, S3 y S4 se generaron con el árbol sin commitear (sobre `1e7f2ca`) **antes** de dos cambios que no
alteran números donde no se activan: la corrección de las etiquetas de procedencia del resumen y la falla explícita de
la entrada supersónica. Esta última no se activa en el ejemplo (Mach máximo de cara de entrada 0,6, ver `audit/`). S4
no se repitió. Los archivos de S2/S3/S4 no registran `code_dirty`; los de S2b y `audit/` tampoco. La reproducibilidad
exacta de esos estudios por commit **no está garantizada**; la reproducibilidad de los *ejemplos* sí (`code_dirty=false`).
