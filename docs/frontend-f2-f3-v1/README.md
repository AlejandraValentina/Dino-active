# Dino F2/F3 · candidato integrado rc14

Main local quedó consolidado por fast-forward a `97e40bd`. F2/F3 vive en feat/dino-frontend-f2-f3-v1. El candidato corregido se construyó limpio desde `b00a5653`; su código de producto coincide con la fuente aceptada `e9a817c`. No se hizo push ni publicación.

IMPLEMENTED · SOURCE_ACCEPTED · WINDOWS_ACCEPTED. UAT humana y accesibilidad integral pendientes. Validación experimental NOT_PERFORMED y capacidad predictiva NOT_CLAIMED. La regresión general completa conserva GENERAL_REGRESSION_NOT_GREEN heredado; CP3/CP4 y esa deuda siguen en su línea separada.

## Abrir desde PowerShell

Desde la raíz de este worktree:

```powershell
$dinoCandidate = Get-Content results/frontend-f2-f3-v1/candidate.json -Raw | ConvertFrom-Json
$dinoSessionRoot = Split-Path (Split-Path (Split-Path $dinoCandidate.folder))
$env:DINO_ARTIFACT_ROOT = Join-Path $dinoSessionRoot 'user-artifacts'
& (Join-Path $dinoCandidate.folder 'Dino2T.exe')
```

Dino2T.exe es la entrada común de las tres familias. El selector permite 2T, 4T nativo o 4T 0D de referencia. Preparar muestra la carpeta de resultados: verificá esa ruta si existía una preferencia anterior.

## Recorrido de trabajo

1. Elegí la familia y MODELO. Componentes abre el esquema funcional; seleccionarlo lleva al formulario físico. Aplicar actualiza la identidad visible. El esquema no está a escala ni pretende ser CAD.
2. SIMULAR conserva los controles propios del modelo. Corridas y cola abre historial, vinculación verificada y cola persistente de puntos 2T/nativos; desde allí se accede a curvas 0D. Cada entrada queda congelada con sus presupuestos e identidad. Pausar espera el punto actual; cancelar conserva resultados parciales disponibles.
3. RESULTADOS → Ampliar permite inspeccionar valores completos. Flechas recorren muestras existentes; más/menos o rueda amplían; Inicio restablece; botón central desplaza. Muestras muestra ausencias y estados. Exportar ofrece CSV y PNG. Los estados no convergidos conservan su calificación.
4. Herramientas → Diferencias compara la configuración aplicada con base. El nativo admite renombrar variantes y undo/redo. El A/B de resultados exige el contrato de elegibilidad existente y sólo después superpone presiones verificadas.
5. Archivo → Recuperar borrador permite elegir por modelo/nombre/fecha/origen. Posponer conserva entradas. Abrir crea una copia sin ruta; Guardar requiere SaveAs. Las referencias 0D ahora usan claves V2 separadas, incluso cuando nombres distintos se sanitizan igual en Windows; los borradores V1 se conservan.

Atajos: Ctrl+1 / Ctrl+2 / Ctrl+3 → Modelo/Simular/Resultados; Ctrl+Shift+M → Componentes; Ctrl+Shift+R → Corridas; Ctrl+Shift+D → Diferencias; Ctrl+Shift+O → Recuperación. También están expuestos en los menús.

## Evidencia y límites

| Verificación | Resultado |
|---|---|
| Regresión combinada del frontend e integración | 120 PASS |
| Cambios finales de recuperación, CP0/CP1/CP2 y presentación | 26 PASS focalizados; no sumables por solapamiento |
| Contratos protegidos P4–P8 | 301 PASS, 3 SKIP; 4 warnings NumPy heredados |
| Aplicación Windows real desde fuente | 47 base + 78 F2/F3 |
| Ejecutable congelado fuera del repositorio | 47 base + 78 F2/F3 |
| CP1 / CP2 empaquetados | 14 / 8 comprobaciones |
| Recuperación externa Windows UIA | 12 comprobaciones, tres familias |
| Recibo final de hashes, árboles, contratos y procesos | 36 comprobaciones PASS |

La suite combinada de 120 corresponde a la base de integración; los cambios finales se cubren con 26 pruebas focalizadas y recorridos completos. Los conteos se solapan y no se suman.

Los recorridos usan corridas reales acotadas y fixtures A/B explícitamente sintéticas. Finalizar no demuestra periodicidad, y periodicidad no demuestra validación experimental. No se modificaron solvers, ecuaciones, tolerancias, tests protegidos ni implementación de licenciamiento.

El primer rc14-552a5673 se conserva como candidato supersedido: pasó sus pruebas previstas, pero la revisión visual encontró la colisión de identidad del autoguardado0D. El candidato entregable `b00a5653` incluye la corrección y repite toda la aceptación Windows. rc13 y sus hashes permanecen intactos.

## Pendientes explícitos

Los 23 hallazgos quedan reconciliados: 12 cerrados funcionalmente, 10 parciales y 1 pendiente de UAT. Entre los parciales están el preparador común de todas las curvas, cola durable universal, explorador común de variantes, catálogo de estados/errores y jerarquía de avisos. No se declaran cerrados por una mejora parcial. Checkpoints nativos requieren una API científica futura; no se fabricó reanudación desde la UI.

- [Arquitectura](architecture.md) y [sistema visual](visual-system.md).
- [Backlog por hallazgo](backlog.md) y [dependencias de backend](backend-capabilities.md).
- [Verificación](verification.md) y [autorrevisión](self-review.md).
- [Recibo final](../../results/frontend-f2-f3-v1/acceptance.json), [candidato/hashes](../../results/frontend-f2-f3-v1/candidate.json), [consolidación](../../results/frontend-f2-f3-v1/consolidation.json).

La raíz externa de esta entrega contiene visual-before-after.html, con capturas originales embebidas y sus hashes en visual-evidence.json. Es una comparación de interfaz, sin claims físicos. El ZIP final pesa 91.670.657 bytes y su SHA-256 es `fda74a5c9113948bcbee366a9a65886e3acf7a84b9115d1c3bc75b7f191f87c4`.
