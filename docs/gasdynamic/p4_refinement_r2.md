# P4_REFINEMENT_R2 — delta de refinamiento, 2026-09-21

Adoptado por orden2df31e6d y revisión independiente read-only /root/p3_review:
**P4_R2_PASS_REFINEMENT_CONTRACT**. No modifica implementación numérica.

## Delta exacto

Ámbito único: refinamiento del blowdown contractual P4B. Histórico en
openspec/changes/p4-escape-1d/design.md y dev_orchestrator/p4_waves.py:
exigía D200,400 < D100,200 para cada observable. Se conserva ese registro,
incluido el FAIL histórico; no se modifica retroactivamente su evaluación.

R2 exige cuatro mallas completas N100/200/400/800; observables congelados R1
antes de N800: sensor físico0,1m, interpolación espacial lineal, Qp integral
lineal temporal de |p−100000|, Qm ledgerSSPRK2, llegada al cruce102000Pa.
Para Qp y Qm, obligatoriamente D400,800 < D200,400. La llegada debe satisfacer
la misma desigualdad. Conservar las tres transiciones, incluida100→200.
También obligatorios: conservación/admisibilidad/CFL, temporal pequeño según
R1 y control simple independiente convergente. No tolerancia absoluta/relativa
nueva, exclusión de mallas, cambio de observable ni Richardson formal.

Se elimina únicamente la obligatoriedad de D200,400 < D100,200 en blowdown.
Difusor, E06–E11 y restantes gates no cambian.

## Fundamento y límites

Un observable mezcla errores de fase, amplitud, discretización de eventos y
acoplamiento. Ni siquiera una expansión e(h)=a*h+b*h² con signos opuestos
garantiza monotonía en mallas gruesas: puede haber cancelación. Este argumento
no ajusta coeficientes a MotorSim ni prueba un régimen asintótico del caso.
En ondas fuertes/contactos no se puede trasladar sin más el orden formal de
regiones suaves. Referencia primaria de contexto:
[Ketcheson, Parsani y LeVeque, High-order wave propagation algorithms](https://numerics.kaust.edu.sa/papers/sharpclaw2011/sharpclaw.pdf).
La decisión contractual se apoya en evidencia local, no en esa referencia como
garantía de monotonía o suficiencia de malla.

Interpretación autorizada exacta:
**verified refinement contraction over the tested fine-grid transition**.
No asymptotic convergence proven, orden formal, error absoluto certificado,
generalización a otra geometría o validación experimental. Tampoco acredita
la malla del motor híbrido, que necesita su propio diagnóstico.

## Evidencia y revisión previa a P4C

R1/R1E fijaron la condición fina antes de N800. Cuatro completos, mismos
observables; contracciones Qp0,409777588, Qm0,732662663, llegada0,545954037.
Temporal/control/conservación/admisibilidad/CFL PASS. El fallo de auditoría
tupla/listaR1E se conserva y su corrección offline está documentada.
El reviewer confirmó ausencia de selección retrospectiva y defendibilidad
únicamente con la semántica limitada anterior. Evidencia R1/R1E intacta.

P4B se reevalúa offline con sus16 casos y6 agregados distintos del refinamiento
de blowdown intactos. BajoR2: P4B_PASS_EXHAUST_WAVE_PHYSICS. No se repite N800.
La orden actual habilita P4C tras este registro; no acepta P4 ni habilita P5.
