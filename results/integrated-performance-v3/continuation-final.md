# Performance V3 — cierre de la prueba de equivalencia

**Resultado: B — EQUIVALENCIA NO DEMOSTRADA.** Tras 40 ciclos adicionales y 172.30 s, el detector conserva periodicidad local (racha 43), pero 51/413 observables siguen fuera del contrato. Performance V3 se congela; warm start no se adopta ni se amplía. La curva periódica aceptada continúa usando inicialización independiente.

## Comparabilidad e integridad

La configuración A10000 histórica y la warm coincide en geometría, malla/topología, RPM, límites, EOS, combustión, modelo térmico y controles. Solo difieren los estados iniciales transferidos (`initial_chambers`, `initial_duct_states`, `duct_species`). Se compararon registros de ciclo al mismo límite de 360° (fase 0° CA), con unidades y fórmulas de `REFERENCE_PERIODIC_CONVERGENCE_V2`; el método compara observables y no reescribe identidades. El cálculo ciclo 15 reprodujo exactamente los 102 fallos del comparativo previo. Hashes de referencia, checkpoint original y continuación verifican en `continuation-comparison.json`.

## Evolución, ciclo 16–55

Cada fila compara los observables de ese ciclo con el ciclo periódico 104 independiente, a fase 0° CA. “Δ quemado escape 30” es diferencia absoluta de fracción másica; sus tolerancia es 0.002. Las diferencias de masa/temperatura y especie global usan las normalizaciones del contrato.

| Ciclo | Fallos / 413 | Razón máx. / límite | Δ quemado escape 30 | Δ masa escape máx. | Δ T escape máx. | Δ especie global máx. | Racha |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 16 | 102 | 17.0645 | 0.0341291 | 0.0181931 | 0.017175 | 0.0198645 | 4 |
| 17 | 101 | 17.319 | 0.034638 | 0.0177543 | 0.0167735 | 0.0194168 | 5 |
| 18 | 102 | 17.5478 | 0.0350957 | 0.0172653 | 0.0163201 | 0.0189696 | 6 |
| 19 | 101 | 17.7499 | 0.0354998 | 0.016829 | 0.0158743 | 0.0185236 | 7 |
| 20 | 100 | 17.9242 | 0.0358484 | 0.0164215 | 0.0155021 | 0.0180793 | 8 |
| 21 | 99 | 18.07 | 0.0361399 | 0.0159772 | 0.0150918 | 0.0176373 | 9 |
| 22 | 99 | 18.1868 | 0.0363735 | 0.0155238 | 0.0146472 | 0.0171985 | 10 |
| 23 | 99 | 18.2746 | 0.0365492 | 0.0151277 | 0.0142671 | 0.0167637 | 11 |
| 24 | 98 | 18.3338 | 0.0366676 | 0.0147021 | 0.013875 | 0.0163338 | 12 |
| 25 | 97 | 18.3653 | 0.0367307 | 0.0142502 | 0.0134557 | 0.0159095 | 13 |
| 26 | 95 | 18.3704 | 0.0367408 | 0.0138279 | 0.0130278 | 0.015492 | 14 |
| 27 | 95 | 18.3507 | 0.0367014 | 0.013403 | 0.0126364 | 0.0150819 | 15 |
| 28 | 95 | 18.3081 | 0.0366161 | 0.0129577 | 0.012224 | 0.0146801 | 16 |
| 29 | 93 | 18.2446 | 0.0364891 | 0.0124954 | 0.011794 | 0.0142874 | 17 |
| 30 | 93 | 18.1625 | 0.0363249 | 0.0120505 | 0.0113501 | 0.0139046 | 18 |
| 31 | 92 | 18.064 | 0.0361279 | 0.0116018 | 0.0109315 | 0.0135322 | 19 |
| 32 | 92 | 17.9513 | 0.0359027 | 0.0111427 | 0.0105046 | 0.0131707 | 20 |
| 33 | 91 | 17.8267 | 0.0356535 | 0.0106767 | 0.0100701 | 0.0128207 | 21 |
| 34 | 90 | 17.6922 | 0.0353845 | 0.0102069 | 0.00963104 | 0.0124824 | 22 |
| 35 | 90 | 17.5498 | 0.0350996 | 0.00973862 | 0.00919059 | 0.0121561 | 23 |
| 36 | 88 | 17.4012 | 0.0348024 | 0.00928394 | 0.00875153 | 0.0118419 | 24 |
| 37 | 87 | 17.2481 | 0.0344962 | 0.00883204 | 0.00831641 | 0.0115399 | 25 |
| 38 | 86 | 17.0919 | 0.0341839 | 0.00838534 | 0.00789772 | 0.0112502 | 26 |
| 39 | 86 | 16.934 | 0.033868 | 0.00794598 | 0.0074862 | 0.0109725 | 27 |
| 40 | 85 | 16.7755 | 0.033551 | 0.00751581 | 0.00708284 | 0.0107069 | 28 |
| 41 | 84 | 16.6174 | 0.0332348 | 0.00709639 | 0.00668917 | 0.0104532 | 29 |
| 42 | 84 | 16.4606 | 0.0329211 | 0.00668902 | 0.0063065 | 0.010211 | 30 |
| 43 | 82 | 16.3057 | 0.0326114 | 0.00629473 | 0.00593585 | 0.00998009 | 31 |
| 44 | 80 | 16.1534 | 0.0323069 | 0.00591432 | 0.00557803 | 0.00976023 | 32 |
| 45 | 79 | 16.0043 | 0.0320085 | 0.00554837 | 0.00523362 | 0.00955104 | 33 |
| 46 | 68 | 15.8586 | 0.0317172 | 0.00519726 | 0.00490303 | 0.00935218 | 34 |
| 47 | 66 | 15.7168 | 0.0314335 | 0.00486121 | 0.00458649 | 0.00916329 | 35 |
| 48 | 65 | 15.579 | 0.031158 | 0.0045403 | 0.00428411 | 0.008984 | 36 |
| 49 | 64 | 15.4455 | 0.030891 | 0.00423445 | 0.00399583 | 0.00881392 | 37 |
| 50 | 61 | 15.3164 | 0.0306328 | 0.00394351 | 0.00372153 | 0.00865268 | 38 |
| 51 | 52 | 15.1918 | 0.0303835 | 0.0036672 | 0.00346098 | 0.00849989 | 39 |
| 52 | 52 | 15.0716 | 0.0301433 | 0.0034052 | 0.00321387 | 0.00835519 | 40 |
| 53 | 52 | 14.956 | 0.0299121 | 0.00315711 | 0.00297984 | 0.00821819 | 41 |
| 54 | 51 | 14.8449 | 0.0296898 | 0.00292249 | 0.00275849 | 0.00808855 | 42 |
| 55 | 51 | 14.7382 | 0.0294765 | 0.00270086 | 0.00254937 | 0.0079659 | 43 |

Las diferencias de masa y temperatura del escape cayeron monotónicamente entre ciclos 16 y 55 (85.2%); el máximo desvío de especies globales cayó 59.9%. La fracción quemada en la celda 30 bajó 13.6% en neto, con 29 descensos y 10 aumentos entre ciclos adyacentes. Los fallos totales bajaron 102→51. Por tanto, hay relajación del estado espacial, pero las especies residuales siguen muy fuera de tolerancia al final.

## Comparación física final

| Magnitud | A10000 independiente, ciclo 104 | Warm, ciclo 55 | Diferencia |
|---|---:|---:|---:|
| Trabajo indicado / ciclo (J) | 32.9269 | 32.9141 | -0.0389% |
| Potencia indicada (W) | 5487.82 | 5485.69 | -0.0389% |
| Potencia freno (W) | 3523.7 | 3521.63 | -0.0588% |
| Torque freno (Nm) | 3.36489 | 3.36291 | -0.0588% |
| Aire atrapado (mg) | 28.9213 | 28.9122 | -0.0315% |
| Carga fresca atrapada (mg) | 32.4769 | 32.4671 | -0.0301% |
| AFR atrapado | 8.13409 | 8.13309 | -0.0123% |
| Combustible quemado (mg) | 1.96485 | 1.96419 | -0.0333% |
| Calor químico (J) | 71.8151 | 71.7912 | -0.0333% |

Las presiones mínimas/máximas de cárter, cilindro y escape difieren entre -0.0040% y +0.0123%. Conservación relativa final: masa 2.92e-15, energía 2.31e-15, especies 5.03e-15; no aparece defecto de conservación ni error de integración.

Persisten **51/413 fallos**: 49 en escape (18 especies quemadas, 18 residuales, 13 masas de celda) y 2 en inventarios globales (quemado y residual). No fallan los observables de presión, energía, temperatura ni velocidad en celdas del escape al final; esto no neutraliza la discrepancia material de composición espacial. `exhaust[30].species.burned` termina en Δ=0.0294765 frente a 0.002 (14.74×).

## Tiempo y decisión

La invocación calculó 40 ciclos nuevos (16–55) en 172.30 s; tiempo de solver 141.21 s, procesamiento 16.86 s, RSS máximo 128.9 MiB. El checkpoint de ciclo 15 quedó preservado en `invocation-001`; la continuación escribió checkpoint completo de ciclo 55.

**Decisión final B:** equivalencia no demostrada dentro del presupuesto. No es un error físico/numerico demostrado: conservación e integración pasan y las diferencias espaciales disminuyen, pero 51 observables aún exceden los límites. No continuar esta línea con más ciclos o campañas; V3 queda congelado y el warm start no se incorpora. Priorizar optimizaciones numéricas que preserven inicialización independiente. No se ejecutó ninguna simulación después de este ensayo.

Evidencia completa: [continuation-comparison.json](continuation-comparison.json). SHA-256: `f4f8f8086f5d7f6b21050c51d4a7373822f18a8ce054b141195b2b024bdfd648`.
