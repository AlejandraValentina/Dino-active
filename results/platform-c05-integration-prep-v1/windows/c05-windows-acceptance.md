# C05 — aceptación Windows del candidato `9298cb66`

Fecha: 2026-11-10. Candidato único, no-trial, construido desde el commit
inmutable `9298cb6602485d138972ac603336bf43df0d6f57` con árbol limpio.

## Identidad del candidato

| Dato | Valor |
|---|---|
| Versión | `0.1.0-rc12` |
| Commit fuente | `9298cb6602485d138972ac603336bf43df0d6f57` |
| Build UTC | `20261110T102500Z` |
| Trial | `false` |
| Inputs empaquetados | 281 |
| Manifiesto de inputs SHA-256 | `6fb4aa682e2034f0b5359a7ce76ecb266050521c23f42e0fb32e5aba4b66a259` |
| ZIP | `MotorSim-0.1.0-rc12-windows-x64-9298cb66.zip` |
| ZIP SHA-256 | `6668ca33b20dffdc28d3c3ebd88d1c234919f9b15f03bdcb387f4cd72ece4e43` |
| ZIP bytes | 91 564 443 |
| `Dino2T.exe` SHA-256 | `a1be876c7231ba2ccfabf66c040983c0db099625d7a409dedd29dedf87d1a54c` |
| `MotorSimWorker.exe` SHA-256 | `e56d2eea235b167e2b94d786ab4e17caadcc6c82e9b971d7dbba0daf03e418a6` |
| `build.json` SHA-256 | `507813975f1ef09d317a305c5c4516fa6b5f4b1df8c47d31b4e1020bd9dc8df2` |

Ruta externa del candidato (no publicada):
`E:/Dino-artifacts/Windows/MotorSim-0.1.0-rc12-windows-x64-9298cb66`.
Los recibos y capturas se copiaron a este directorio para conservar la
evidencia; el ZIP no se versiona.

## Resultado

**PASS para el alcance de aceptación Windows solicitado.** El candidato
ejecuta el worker congelado, enruta 2T/4T, abre y reabre proyectos, calcula y
persiste curvas RPM 4T, cancela una curva conservando un resultado parcial,
exporta CSV/HTML, muestra trazabilidad y cierra sin workers huérfanos.

| Prueba empaquetada | Evidencia | Resultado |
|---|---|---|
| `MotorSimWorker.exe` 2T: punto de referencia | `frozen-worker-acceptance.json` | PASS, `converged` |
| `MotorSimWorker.exe` 2T: curva 2500/3000/3500 | `frozen-worker-acceptance.json` | PASS, 3/3 `converged` |
| `MotorSimWorker.exe` 4T: punto de referencia | `frozen-worker-acceptance.json` | PASS, `converged` con metadatos de modelo |
| `MotorSimWorker.exe` 4T: curva 2500/3000/3500 | `frozen-worker-acceptance.json` | PASS, 3/3 `converged` |
| Ruta 2T → 4T → 2T | `route-2t-4t-acceptance.json` | PASS, una sola ventana, sin solver |
| Curva RPM 4T completa | `four-stroke-curve-acceptance.json` | PASS, 3 puntos convergidos |
| Persistencia y reapertura de la curva | `four-stroke-curve-acceptance.json` | PASS, `curves/<series_id>/series.json` restaurada |
| Cancelación de curva 4T | `four-stroke-curve-acceptance.json` | PASS, referencia parcial `cancelled` persistida |
| Histórico 4T legacy | `legacy-4t-acceptance.json` | PASS, ambos endpoints `LEGACY_UNVERIFIED` |
| Trazabilidad | `legacy-4t-acceptance.json` | PASS, integridad, run, config SHA-256 y commit |
| Exportación CSV | `legacy-4t-results.csv` | PASS, dos filas legacy con hashes |
| Informe HTML | `legacy-4t-report.html` | PASS, `No realizado` / `No declarado` |
| Reapertura en proceso nuevo | `legacy-4t-acceptance.json` | PASS, historial legacy conservado |
| Cierre de recursos | todos los recibos | PASS, sin `MotorSimWorker.exe` ni `Dino2T.exe` |

Las capturas de la curva 4T (completa, reabierta y cancelada) y la captura 2T
del ruteo están en este directorio.

## Fallos Qt investigados por separado

1. **Corrida focalizada inicial (`c05-focused`)**: un test llamaba a
   `FourStrokeSimulation._finished()` con la firma anterior; el fallo no se
   limpió y el proceso de pytest terminó con código Windows
   `3221226505` (`0xC0000409`) durante el teardown de Qt. Se corrigió el test
   en `ffc89b3` para usar el token y limpiar el widget en `finally`; la corrida
   final (`c05-focused-final2`) terminó con exit 0 y **249 PASS + 1 SKIP**.
   Es un defecto de arnés/teardown, no un crash del solver ni del paquete.
2. **Driver A/B inicial (`c05-win-ab`)**: no fue un crash. El script esperaba
   endpoints verificados, pero el proyecto histórico contiene referencias
   legacy; la política estricta las rechazó correctamente y el driver falló
   por su propia aserción de comparación. La app no promovió el histórico. Se
   reemplazó ese recorrido por la aceptación legacy, que PASS y verificó el
   comportamiento fail-closed, la trazabilidad y las exportaciones.
3. **Automatización UIA de la curva**: los intentos iniciales fallaron por
   diálogos nativos de guardado y por exposición UIA de tablas; no hubo crash
   de Qt. El recorrido final automatizado PASS.

No se encontraron eventos `Application Error`/`Windows Error Reporting` para
`Dino2T.exe`, `MotorSimWorker.exe`, `MotorSim.exe` ni `python.exe` durante la
ventana de aceptación. No se atribuyen los dos fallos anteriores a una causa
común.

## Límites explícitos

- **Comparación A/B estricta con los endpoints históricos: no ejecutada.**
  Esos endpoints son legacy y la política `STRICT_SOURCE_V1` exige inventario
  de fuente limpio; la app correctamente no los promociona. Una comparación
  A/B nueva exigiría un par de corridas 4T desde fuente limpia y no forma
  parte de esta aceptación puntual. La lógica estricta está cubierta por las
  suites de fuente.
- **Curva RPM 2T en UI: no reejecutada.** Se ejecutó la curva 2T en el worker
  congelado y el ruteo 2T/4T; la UI 2T no cambió en C05.
- **Sin claim científico:** calibración `NOT_PERFORMED`, validación
  experimental `NOT_PERFORMED`, predictiva `NOT_CLAIMED`.
- El paquete no se publica y no se ejecutó push. El fast-forward a `main` se
  realiza sólo después de registrar esta evidencia.

## Índice de evidencia

- `candidate.json` — identidad y hashes del candidato.
- `candidate-build.json` — metadatos completos del build.
- `candidate-zip.sha256` — hash del ZIP.
- `frozen-worker-acceptance.json` — worker congelado 2T/4T, puntos y curvas.
- `route-2t-4t-acceptance.json` — ruteo 2T/4T.
- `four-stroke-curve-acceptance.json` — curva 4T, persistencia, reapertura y
  cancelación.
- `four-stroke-curve-*.png` — capturas de la curva.
- `legacy-4t-acceptance.json` — histórico legacy, trazabilidad y reapertura.
- `legacy-4t-results.csv`, `legacy-4t-report.html` — exportaciones.
- `route-2t-project-1360x900.png` — captura del ruteo 2T.
