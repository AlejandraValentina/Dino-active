# DINO 2T Performance V2 — resultado medido

Estado: PASS para esta optimizacion focalizada. No se ejecuto una curva completa ni una campana RPM.

## Perfil CPU antes del cambio

Se perfilaron tres ciclos de A9000 y B9000 con el solver actual antes de V2. `cProfile` elevo el tiempo de proceso a 50,50 s (A) y 49,15 s (B); no se usan esos tiempos para speedup. Ambos perfiles tienen el mismo orden de costos:

- `validate_species`: 3,42 s (A) / 3,31 s (B) exclusivos, ~914 mil llamadas.
- `IntegratedEngine2T._assemble`: 3,13 / 3,01 s exclusivos.
- `all` y `math.isfinite`: 3,01 / 2,94 s y 2,92 / 2,87 s; llamadas/generadores de validacion.
- HLLC `hllc_flux`: 2,29 / 2,24 s exclusivos; EOS `validate`: 1,89 / 1,85 s; `deepcopy`: 1,37 / 1,35 s.

Los tiempos acumulados se solapan; no se suman. El profiling tarda aproximadamente cuatro veces mas que las corridas normales. Las corridas normales separan el tiempo de pasos del integrador (~11,1 s) del procesamiento posterior (~0,69 s). La persistencia no aparece como cuello dominante de CPU; la espera pura de disco no se aislo.

En los dos perfiles, por subsistema, `IntegratedEngine2T` acumula ~10,5-10,9 s exclusivos; EOS ~7,5-7,7 s; P6 species ~6,6-6,7 s; HLLC/Riemann ~3,8-3,9 s; termica ~1,7-1,8 s; puertos/reed/plenum ~2,7 s combinados; combustion ~0,52-0,56 s; y crankcase ~0,46-0,48 s. El integrador SSPRK2 `step` suma ~0,64-0,67 s exclusivos en 2.163 llamadas (tres ciclos), y `_combine` ~0,16-0,17 s; la mayor parte de SSPRK2 es el ensamblado dos veces por paso. `_port_face_flux` consume ~0,06 s y `_geometry` ~0,11 s. `deepcopy` suma ~1,35-1,37 s, señal de asignaciones/copia de estado. El runner de diagnosticos y checkpoints usa ~0,65-0,69 s exclusivos; `atomic` ronda 0,001 s perfilado. No se perfilaron el render de Desktop ni la presentacion visual.

## Cambios implementados

1. En `IntegratedEngine2T._face_species_flux`, el signo del flujo selecciona el donante. Se normaliza solo su estado, en vez de validar y normalizar ambos lados de cada cara. `step()` ya valida todos los estados al borde de cada etapa SSPRK; permanece la validacion de `donor_species`, y flujo cero conserva la validacion de ambos lados.
2. `validate_species` reutiliza sin copia las tuplas inmutables de cuatro floats que produce el solver. Las listas/tuplas con enteros siguen la conversion generica. Se mantienen todas las comprobaciones finitas, no negatividad y suma de masa.

No cambiaron ecuaciones, flujo HLLC, geometria, puertos, combustion, CFL, tolerancias ni periodicidad. No se agrego Numba ni otra dependencia.

## Rendimiento sin profiler

Cada caso tiene tres repeticiones antes y tres despues, alternadas por configuracion; cada invocacion calcula exactamente tres ciclos y 721 pasos aceptados por ciclo.

| Configuracion | Tiempo proceso antes | Despues | Mejora | CPU antes | Despues | Solver por paso antes | Despues | RSS pico antes | Despues |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A9000 | 12,409 s | 11,371 s | 8,36% | 12,250 s | 11,063 s | 5,249 ms | 4,722 ms | 102,01 MiB | 101,91 MiB |
| B9000 | 12,179 s | 11,265 s | 7,50% | 11,969 s | 11,047 s | 5,130 ms | 4,710 ms | 102,02 MiB | 101,98 MiB |

El tiempo de procesamiento posterior fue 0,695 -> 0,714 s en A y 0,700 -> 0,704 s en B. El pequeno aumento de A esta dentro de la variacion y no oculta la reduccion del tiempo solver. Las medianas no muestran aumento de memoria. No se midio conteo de asignaciones; las asignaciones evitadas se infieren del camino de codigo y el RSS pico si se midio.

## Equivalencia, conservacion y restart

Se compararon seis pares de corridas (A/B, tres repeticiones por caso). Los diagnosticos de los tres ciclos, snapshots completos de checkpoint y el historial del detector tuvieron **cero diferencias**, excluyendo tiempo, RSS y hashes de artefactos. En todos: 721 pasos aceptados por ciclo, cero rechazos; trabajo, calor de combustion, presion maxima, estados de especies y ledgers conservaron igualdad exacta. Los residuos relativos de conservacion quedaron en los rangos existentes (~1e-16); no se realizo una auditoria independiente nueva.

En A se retomo desde el checkpoint de tres ciclos y se ejecuto el ciclo 4. La restauracion fue exacta, no avanzo pasos fisicos durante la restauracion y el diagnostico y checkpoint de ciclo 4 coincidieron exactamente con una ejecucion continua de cuatro ciclos.

Regresion focalizada: **130 PASS**, 201,8 s, sobre especies P6, IntegratedEngine2T, combustion, checkpoint/replay y las pruebas de equivalencia V2.

## Efecto practico y limites

Aplicando el promedio de los speedups cortos A/B al calculo previo de V1, la proyeccion pasa de **49,18 a 45,28 minutos** para seis puntos (aprox. 3,9 minutos menos). Esto sigue siendo una proyeccion: no se recalcularon los seis puntos y ningun caso corto alcanzo periodicidad (`MAX_CYCLES_NONCONVERGED`). La optimizacion mejora alrededor de 8% el trabajo medido a 9000 RPM en estas dos variantes; no prueba la misma ganancia en otros RPM, mallas o ciclos tardios.

Riesgos restantes: HLLC, EOS y assembly siguen entre los costos principales. No se continuo con ellos porque este cierre autoriza una primera mejora focalizada y no una migracion amplia; cualquier siguiente optimizacion debe partir de un perfil nuevo. Los resultados y checkpoints historicos se conservaron.

## Reproducibilidad

- Fuente antes: `69b4011`; fuente optimizada: `f803c27`.
- Configuraciones originales existentes A9000/B9000, SHA registrados en `measurements.json`.
- Datos detallados y hashes externos: `measurements.json` y `artifact-index.json`; los archivos brutos permanecen bajo `${DINO_ARTIFACT_ROOT}/integrated-performance-v2/`.
- Commits locales: `401dc1d`, `69b4011`, `db928a4`, `f803c27`; sin push.
