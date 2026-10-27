# Checkpoint25: representación inicial y evolución, v1

Diagnóstico L1, SELF_REVIEW; no gate de validación. Origen: checkpoint nativo25
de A9000 sintético, configuración y fuentes verificadas por el runner previo.
No es X30, no warm start de producción, no nueva formulación física.

## Experimento preregistrado

- Dos familias físicas iniciales: P0 constante y P1 lineal limitada dentro de
  las celdas originales44. P1 es una hipótesis explícita sobre información
  subcelda desconocida. No se reconstruye recursivamente desde88 a176.
- Promedios conservados de Euler y cuatro especies; centroides/volúmenes exactos
  de troncos de cono. Minmod en conservadas; pendientes de densidad y marcador
  coherentes con especies; theta común reduce pendientes si la admisibilidad
  falla en caras. Sin recortar caudales, medias, especies ni presión.
- Las dos familias tienen los mismos promedios44. Verificar con tests
  conservación global/local, admisibilidad, consistencia lineal, conmutación
  proyección/restricción, estado original intacto e identidad nativa estricta.
- Un ciclo9000–9360°, fases cada30°. Casos nuevos44/P0/.125°,88/P1/.125°,
  176/P0/.125°,176/P1/.125°. Reutilizar88/P0/.125° ya calculado; no repetirlo
  salvo defecto demostrado en su evidencia. Mismo CFL, detector y física.
- Presupuesto:120s44/88,240s176 por caso,720s agregados,64MiB estimados.
  Preflight reserva2GiB. Detener ante conservación relativa>1e-12,
  inadmisibilidad, incompatibilidad o presupuesto. No ampliar automáticamente.
  Estados FAST+receta por30°, checkpoint nativo al completar ciclo.
- Registrar pasos reales: cap nominal no demuestra control temporal. Las
  referencias existentes44(.5/.25),88(.25/.125) acotan sólo esos contrastes;
  no certifican error temporal176. Si176 reduce pasos por CFL, explicitarlo.

## Comparación y decisión

Restricción conservativa a volúmenes comunes44 y88, fases idénticas. Normas
L1/L2/Linf presión/densidad/especies, perfiles y frentes; conservar diferencias
iniciales y su evolución separadas. Comparar sensibilidad P0/P1 a malla fija con
44/88/176 en cada familia. Separar caudal bruto saliente, entrante y neto por
interfaz, inventarios, trabajo e IMEP. Presión desde medias conservadas y media
de presión no son intercambiables; registrar su diferencia si resulta material.

Orden observado sólo si monótono y compatible con régimen asintótico; no GCI
forzado para frentes. No extrapolar este transitorio a periodicidad ni potencia
periódica. Conservar controles/evidencia y rc7. Si sensibilidad de evolución
domina ambas familias, localizar su origen antes de campañas periódicas. Si
representación domina, cuantificar esa incertidumbre sin atribuirla al solver.
