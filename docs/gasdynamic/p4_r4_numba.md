# P4-R4: evaluación computacional serial

Orden 8f6dbacb. No modifica física, contratos, CFL, malla ni fuentes.
Entorno previo: Windows x64, Python 3.11.0, NumPy 2.3.0. Instalados en .venv
Numba 0.62.1 y llvmlite 0.45.1 mediante wheels cp311-win_amd64; pip check PASS.
Compatibilidad: https://numba.readthedocs.io/en/latest/release/0.62.0-notes.html
NumPy/Python conservados. Sin packaging ni configuración global.

## Definición previa a mediciones

Primer candidato: HLLC, 16.0133 s inclusivos / 63.6825 s instrumentados R3
(25.15%). No sumar porcentajes inclusivos anidados. Sólo después de equivalencia
y ganancia medible se amplía cobertura. float64, njit fastmath=False,
parallel=False, cache=True. Excepciones delegadas al HLLC escalar congelado.

Equivalencia fijada: abs(a-b) <= 1e-13 + 1e-10*abs(a); para presiones,
atol=1e-8 Pa. Eventos, ramas, contadores, admisibilidad y gates iguales.
Si una diferencia de roundoff altera etapas, documentarla antes de aceptar;
no relajar tolerancias ni aceptar cambios PASS/FAIL. Primer ensayo exige
igualdad de etapas. Validadores históricos y balances contractuales intactos.

JIT separado del runtime; cache en proceso nuevo separado. Microbenchmark
HLLC primero; focal >=1.2x antes del ciclo completo. Dos G1 independientes,
mediana <=20s y proyección <=600s habilitan periodicidad; 20–25s NEAR_TARGET,
>25s NATIVE_EXTENSION_DECISION_REQUIRED. No seleccionar el mejor tiempo.
Si no pasa performance, no ejecutar periodicidad/G2. Sin P5/publicación.

Primer kernel: equivalencia PASS; G1 caras480° 1.51879x. Diagnóstico aleatorio
0.98782x conservado. Habilita ampliar sólo primitivas (7.50%) y MUSCL
(11.27% inclusive); no sumar validación anidada. Sin alterar control SSPRK2.
