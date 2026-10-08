# P4-R13A: cierre del evidence gap 56 vs 54

Se reconstruyó únicamente 51–54 desde el restart exacto N400 ciclo50 de R12.
El terminal regenerado de ciclo54 coincide bitwise con el restart R12: estado,
celdas, ángulo y ciclo. El gate es `P4_R13A_CYCLE54_REPLAY_EQUIVALENCE_PASS`.

Usando la función contractual de periodicidad y el `full_cycle56.json.gz` ya
existente de R13, 56 vs 54 da PASS con `sensor_max = 0.0011905119731371136`.
El sensor dominante es 0, fase 132,5°, diferencia 132,61130455836246 Pa,
denominador 111390,14772687998 Pa y métrica 0,0011905119731371136.

Secuencia par completa: 50 PASS, 52 PASS, 54 FAIL (0,009046195029969764),
56 PASS, 58 PASS, 60 PASS. Por tanto R13 se corrige a
**`P4_R13_N400_EVEN_EVENTUAL_CLOSURE`**. El FAIL de 54 permanece visible como
excursión previa; no implica P4 PASS. No se inició E13-R1 ni P5 y no se
ejecutaron ciclos posteriores a 60.
