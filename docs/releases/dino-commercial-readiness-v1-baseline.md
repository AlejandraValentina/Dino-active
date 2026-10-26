# Dino Commercial Readiness V1 — baseline funcional congelada

Estado: aceptada por el propietario como **PASS funcional TRIAL** el 2026-10-26.
Esta versión queda congelada como baseline de producto para el siguiente trabajo
de capacidad predictiva y rendimiento. No implica validación experimental,
predictiva, científica ni comercial.

## Identidad aceptada

- Aplicación: Dino 2T Desktop `0.1.0-rc7`, paquete Windows x64 TRIAL.
- Commit fuente limpio: `fc27542155840cdadbcc2b591ae5cd8e99031899`.
- Commits de Commercial Readiness V1: `7c79016` (flujo de diseño nuevo),
  `eb143f6` (editores), `fc27542` (identidad nueva de corrida y corrección de
  comparación), `d048ab4` (aceptación y recibo) y `82002e5` (delta de auditoría).
- ZIP aceptado: `MotorSim-0.1.0-rc7-windows-x64-fc275421-trial-20261026T104414Z.zip`.
- SHA-256: `2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
- El recibo de aceptación y las limitaciones completas están en
  `results/dino-commercial-readiness-v1/acceptance/receipt.json`.

## Evidencia y límites

- Regresión focalizada: 28 PASS.
- Recorrido desde EXE: creación y guardado, variante de escape +20 mm, dos
  corridas integradas breves a 3000 RPM, comparación, exportación CSV y
  recuperación del proyecto después de cerrar y relanzar.
- Las dos corridas son `MAX_CYCLES_NONCONVERGED` / `INSUFFICIENT_CYCLES` y
  comparaciones `EXPLORATORIO` con advertencia transitoria. No son curvas
  estacionarias ni prestaciones validadas.
- No se cambió X30, solver, física ni umbrales; no se afirma validación
  experimental o comercial.
- El comparador ya no añade puntos RPM del recipe a corridas locales ajenas al
  proyecto. El par seleccionado compatible se compara por RPM común exacto.

El desarrollo futuro debe tratar esta versión aceptada como baseline y medir
los cambios predictivos/de rendimiento de forma aditiva, sin reconstruir el
flujo de Desktop que ya funciona.
