# P4-R12: auditoría de cierre por paridad

R11 conserva su contrato original: cierre lag-2 global. Su clasificación
`P4_R11_PERIOD2_LAG2_CLOSURE_CONFIRMED` permanece válida bajo ese contrato.
La normalización de booleanos sólo exige JSON booleano (`true`/`false`), no
redefine retrospectivamente el gate de R11.

R12 aplica un contrato más fuerte: las secuencias impar y par se evalúan por
separado y cada una necesita tres PASS consecutivos. N350 continuó sólo desde
`restart_cycle50` hasta los ciclos 51 y 52. El ciclo 52 es PASS; con 48, 50 y
52, la rama par alcanza tres PASS, y la rama impar ya tenía 41, 43, 45, 47, 49.

N400 ya tenía los ciclos 50 y 52 PASS. La auditoría de ciclo 54 confirma que su
estado proviene de la continuación normal desde `restart_cycle50`, con
`NUMBA_FUSED`, CFL 0,4, N400 y float64. `run_cycle` recibe sólo estado, celdas y
ángulo; no usa el historial d1/d2 para integrar. El D2 de 54 compara 54 contra
52 y reproduce `sensor_max = 0.009046195029969764`, por encima de 0,005.
La secuencia par N400 es `[true, true, false]`, máximo 2: no hay cierre por paridad.

Resultado terminal R12: **`P4_R12_ONE_BRANCH_NONCLOSURE`**. No se ejecutan 56/58/60,
no se cambia el umbral, no se inicia E13-R1, P4 PASS ni P5. Conservación y
admisibilidad de N350 ciclo 52 y N400 ciclo 54 permanecen PASS.
