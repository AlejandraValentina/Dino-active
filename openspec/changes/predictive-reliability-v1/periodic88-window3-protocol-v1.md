# Ventana88 número3: nativo39, máximo40–43

2026-10-27. Dependencia resuelta por `7a6d70f`: replay39 exacto, balances por
especie/subsistema y energía PASS; frente de densidad/composición desplazado
con presión casi repetible. No se modifica el solver ni el detector.

## Justificación y límite

La máxima amplitud sigue decreciendo, el incremento por celda del inventario
de quemados disminuye y su cambio neto coincide con transporte; el p90/L1
repuntan al desplazarse la estructura. No es suficiente para declarar
estancamiento de una solución espacial fija. Tampoco permite predecir ciclos
restantes ni afirmar que88 alcanzará el mismo estado que44.

Se autoriza técnicamente UNA ventana desde checkpoint39 nativo14040°, mismo
motor/RPM/malla88, identidad, eventos de combustión y detector relativo9.
Máximo cuatro ciclos completos40–43 (relativos10–13),210s de solver,
230s de admisión y watchdog240s. Último coste cuatro ciclos≈157s sin replay;
se estima margen. Preflight16MiB/reserva2GiB, mismos artefactos recuperables.
No nuevas mallas, barridos, RPM, física ni tolerancias.

Verificar antes la restauración nativa completa y que la observación38→39
coincide exactamente con la última del detector. Conservar historia relativa
1–9 y usarla también para el control de estancamiento de recursos.

## Paradas y observación

- Presupuesto, error de admisibilidad/conservación, fallo de identidad o
  candidato periódico: parada inmediata con evidencia según harness vigente.
- Regla de progreso ya existente: con las últimas tres comparaciones válidas,
  si ambas transiciones no reducen el máximo al menos5% y no reducen p90,
  detener por progreso insuficiente. Este5% sólo decide gasto de CPU; no
  cambia umbrales científicos ni periodicidad.
- Registrar por ciclo los809 observables, lag1/lag2, checkpoints, detector,
  recetas y13 fases cada30° sin modificar el paso para muestrear.
- Después, comparar composición L1/L2/Linf, máximo/centro de discrepancia,
  inventarios y presión, trabajo/IMEP. Un desplazamiento aguas abajo no basta
  para aceptar: si empeoran sostenidamente amplitudes/inventarios sin
  explicación o se pierde la estabilización de presión/trabajo, detener
  extensiones y diagnosticar con los estados guardados.
- No ejecutar automáticamente otra ventana,176 ni auditorías extensas.
  Si aparece candidato, preparar replay/L2 de sus períodos antes de admitirlo.

La periodicidad44 auditada es control.88 sigue transitorio hasta prueba
independiente del detector y auditoría. Sin declaración de independencia de
malla ni validación predictiva experimental. rc7 se conserva intacta.
