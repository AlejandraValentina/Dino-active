# C05 + CP0 — aceptación Windows de la base integrada

Fecha: 2026-11-10. Rama de integración:
`integrate/commercial-unified-ui-v1`. `main` no fue modificado.

## Candidato

| Dato | Valor |
|---|---|
| Commit fuente | `f45d60bf728d6c47838e38514854476a3a02e516` |
| Integración | `7ed8566` + `ace5956` + `2fb5cd7` + `f45d60b` |
| Versión | `0.1.0-rc12` |
| Trial | `false` |
| Build UTC | `20261110T142221Z` |
| Inputs empaquetados | 284 |
| Manifiesto SHA-256 | `08b6596d971770d5d88bee78e76ace9528ae7842d5bf60823c6060febccc73d1` |
| ZIP SHA-256 | `f05b00c8d3695e6fcc212672a4563e573031002f98b272bf4b6fa9fe48d7f1e9` |
| ZIP bytes | 91 583 636 |
| `Dino2T.exe` SHA-256 | `e94f9b38646be7aa97c72284e5daa7588482c4f8312916d86608d904ebeabe5a` |
| `MotorSimWorker.exe` SHA-256 | `3a138301e98561687cfed9f88602ebad9b0340383fbda844a6837529a081890e` |

Ruta externa:
`E:/Dino-artifacts/Windows/MotorSim-0.1.0-rc12-windows-x64-f45d60bf`.

## Regresión conjunta

`results/commercial-product-v1/verification/integrated-commercial-unified.summary.json`
→ **271 passed, 1 skipped**, exit 0. Incluye C01–C05, CP0, navegación
unificada, curvas nativas 4T, API/A-B/Desktop, Stage2 y packaging.

## Aceptación empaquetada

| Prueba | Resultado |
|---|---|
| About en 2T, 4T 0D y 4T nativo | PASS |
| Diagnóstico exportable en los tres modos | PASS |
| Router unificado abre proyectos 2T / 4T 0D / 4T nativo | PASS |
| Recientes separados por familia | PASS |
| Pestaña de curva nativa 4T potencia/torque | PASS |
| Recuperación ofrecida y aceptada en los tres modos | PASS |
| Recuperación restaura como copia sin ruta original | PASS |
| Los archivos originales no se modifican | PASS |
| Cierre terminal sin workers/procesos huérfanos | PASS |

Recibo: `acceptance.json`. Diagnostics exportados:
`diagnostico-2t.zip`, `diagnostico-4t0d.zip`, `diagnostico-4tnative.zip`.

## Correcciones de integración

- CP0 ahora reconoce el **4T nativo integrado** en la ventana principal, además
  de 2T y 4T 0D: about, diagnóstico, recientes, autosave y recuperación.
- La recuperación ya **no asigna la ruta del archivo original**. Restaura una
  copia sin ruta; Guardar abre “Guardar como” en los tres modos. Los originales
  permanecen intactos.
- La raíz de autosave/recuperación respeta `DINO_RECOVERY_ROOT`, luego
  `DINO_ARTIFACT_ROOT`, y evita escribir dentro de un worktree Git. En la
  aceptación se usó la raíz de artefactos en E:.

## Nota de transparencia

Un intento previo de automatización dejó un proceso `Dino2T` de prueba vivo
porque el driver falló antes de su cierre ordenado. Se identificó por PID,
se terminó explícitamente y la corrida final no dejó procesos ni workers
huérfanos. No fue un crash del producto ni se ocultó el incidente.

## Límites

- La comparación A/B 4T con endpoints históricos sigue fail-closed (legacy);
  no se promocionó ningún histórico.
- No se ejecutó una campaña científica ni validación experimental.
- CP1 (undo/redo, bundles, PDF, onboarding, batch, comparación/legacy UX),
  CP2 (instalador/update/licencias) y CP3 (datos/validación) siguen abiertos.
- Sin claim: calibración `NOT_PERFORMED`, validación experimental
  `NOT_PERFORMED`, predictiva `NOT_CLAIMED`.
