# P9 v1.0 — Validación experimental de rendimiento indicado 2T

## Estado

`PREREGISTERED` como P9 v1.0 desde el commit de contrato
`ba1dff027d66982aba0aeb7ae6f315fa92346a2c`, fechado 2026-10-01. El receipt
`results/p9-readiness-20261001/preregistration.json` registra fecha, commit y
hashes. El preregistro precede la incorporación o inspección de cualquier
resultado experimental que decidirá P9.

## Why

Los resultados P4–P8 acreditan verificación numérica delimitada, pero no
validación experimental. P8 es sintético y transitorio. P9 necesita fijar de
antemano una comparación indicada reproducible, gates por punto y globales, y
límites de las afirmaciones antes de examinar los datos confirmatorios.

## What Changes

Define P9 v1.0 como validación confirmatoria de rendimiento indicado en una
configuración 2T fija: cualificación periódica previa, dataset y simulación
congelados, comparación reproducible de trabajo/potencia, gates cuantitativos,
auditoría primaria offline y claims limitados. No cambia el solver ni habilita
calibración.

## Objetivo

Evaluar una sola configuración física fija 2T comparando rendimiento indicado
experimental y simulado con gates preregistrados. La afirmación máxima tras un
PASS queda limitada a esa configuración y al dominio de operación ensayado.

## Alcance

- Calificar primero el estado periódico de cada punto con el contrato E13
  vigente, períodos 1/2 y máximo 400 ciclos.
- Congelar datos y configuración; comparar trabajo/potencia indicados, con
  reglas de RPM, errores, MAPE, signo y tendencia fijadas por P9 v1.0.
- Guardar evidencia primaria y auditarla offline, con pruebas negativas.
- Dejar calibración fuera de P9 v1.0.

## Fuera de alcance

Validación universal o predictiva, otras configuraciones de motor, potencia de
freno como gate, ajuste de parámetros, cambios de física/solver/umbrales,
combustión nueva y extrapolación fuera del rango ensayado.

## Estado de entrada

La autorización explícita para iniciar P9 está vigente. El inventario de
readiness no encontró un dataset experimental autorizado. La campaña P8
disponible es sintética y `BOUNDED_TRANSIENT_INDICATED`; no satisface P9-A ni
puede utilizarse como medición. No ejecutar comparación ni declarar PASS/FAIL
hasta que exista dataset adecuado.
