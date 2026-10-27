# Continuación original25→29

2026-10-27. Una invocación preregistrada `42d6022`, sin cambiar solver,
modelo, paso adaptativo, detector ni tolerancias. Native checkpoint25 y
detector25 restaurados exactamente; observaciones25 reconstruidas desde24/25
sin reintegrar historia. Se conservaron checkpoints26/27/28/29 y detector.

| Ciclo |Máximo error/tolerancia|p90|Mediana|Fallidos/413|Trabajo J|
|---:|---:|---:|---:|---:|---:|
|25, referencia|3.34750|.83917|.07909|37|131.111096|
|26|2.74045|.70221|.06038|30|131.130578|
|27|1.85313|.48588|.04594|21|131.106296|
|28|.87950|.34778|.03471|0|131.054710|
|29|.48308|.17888|.01804|0|130.989630|

La máxima discrepancia26–28 corresponde a quemados en exhaust[30]; al29 pasa
a exhaust[15]. La cola deja de dominar y el conjunto mejora claramente.
Los balances globales, con transformación por combustión, cumplen los
controles por ciclo. No apareció evidencia de fallo de transporte que requiera
una corrección. El trabajo cambia ligeramente, dentro de su criterio vigente.

El detector conserva lag1_streak=2, detected_period=None. Los contrastes lag2
siguen FAIL; eso no demuestra una oscilación de período2. **Periodicidad aún
no declarada**: dos comparaciones válidas no sustituyen las tres exigidas.

Tiempo de pared53.710s<90s: solver53.136s, restauración.233s, detector.011s,
serialización≈.120s, comprobación de balances≈.00024s. Coste solver≈13.28s/ciclo.
No benchmark de EXE ni nueva optimización. Terminal10440°, checkpoint nativo29;
conservados también receta, distribución completa, lag1/2 y fuentes/hashes.

24 tests focalizados PASS antes de ejecutar. Evidencia L1/SELF_REVIEW;
`audit_performed=False`, sin validación experimental ni independencia de malla.

La evolución justifica **una única comprobación adicional de ciclo30**,
con presupuesto25s, para completar o rechazar el streak original. Se debe
preregistrar separadamente; no se lanza por este informe y no habilita una
serie de extensiones si falla. Candidato periódico, si aparece, requiere
auditoría de sus primarias; no confundirlo con cierre de E1.
