# P4-C3-R3 — adquisición focal y auditoría independiente

## Alcance

Se ejecutó una única adquisición N=100, CFL=0,2, con el fixture C2 existente
hasta `t=0,004 s`. No se modificaron física, operador, malla, CFL, eventos,
umbrales ni camino productivo. P9 permanece STOPPED/NOT AUTHORIZED.

## Instrumentación

Cada etapa SSPRK2 conserva estados conservativos y primitivos, estado de cámara,
`dt` y la geometría (`areas`, `volumes`, `faces`, `centers`). El auditor no
consume `momentum_face_fluxes`, `momentum_source_sum` ni ningún término de
momento generado por el operador. Recalcula offline la cara izquierda mediante
la referencia ExactRiemann independiente, la cara derecha desde la presión de
pared y la fuente `sum(p_i*(A_right-A_left))`; las unidades son N para fuerzas
y kg·m/s para momento.

`wave_speed_middle` identifica velocidad de onda. Nunca se presenta como
presión; `p_star` sólo aparece como el valor separado de ExactRiemann.

## Resultado de la única adquisición

La revisión supervisora detectó antes del cierre definitivo que los números de
`174b261` eran inválidos por captura pre/post: `stage_a.conservative` y
`stage_a.chamber_state` se tomaban después del commit, mientras
`stage_a.primitive` y el flujo observado eran de `op0` pre-step. Esos números
quedan invalidados por revisión de captura pre/post. La regeneración también
conserva `stage_b = cells1/z1/op1` y `after = cells_new/z_new/ws_new`.
La pared se reconstruye como ghost reflectante físico `(rho,-u,p,Y)` y se
resuelve con `ExactRiemann(last, ghost, EOS).sample(0)`; el auditor no usa el
HLLC productivo para esa cara. No se modificaron física, operador, malla, CFL,
eventos, umbrales ni camino productivo. Artefactos vigentes:
`results/p4-c3-r3-20260928/`; los números de `174b261` están explícitamente
invalidados por la mezcla pre/post-step.

`interface_flux_observed`, `mass_flux`, `energy_flux` y `species_flux` son
cantidades de `op0/stage_a` pre-step; el auditor independiente los compara con
el mismo `stage_a`.

* Retorno: `PASS`; primer sample admisible seleccionado en
  `sample_time_pre_step=0,0026532366020821743 s`, con flujo de masa positivo
  `0,0002698587123830558 kg/s`; el registro histórico se confirma en
  `history_record_time_post_step=0,0026543865163682658 s`.
* Conservación: `PASS`; residuo normalizado máximo
  `1,3929103469155642e-15`, frente al criterio existente `1e-10`.
* Admisibilidad: `PASS`.
* ExactRiemann: `INCONCLUSIVE`; errores relativos por componente
  `(mass,momentum,energy,species)` =
  `(1,7797458457669132e-07, 3,4548877071827627e-06,
  6,581792616275487e-04, 8,898729228831856e-08)` y máximo
  `6,581792616275487e-04`. No existe un threshold contractual aprobado para
  igualdad HLLC–ExactRiemann y no se inventó uno.
* Balance independiente de momento: `INCONCLUSIVE`; residuo absoluto máximo
  reconstruido `5,840234051652552e-06`; `max_relative_residual =
  1,9399428518812518` y `median_relative_residual =
  0,018615083342715104`, usando `max(|predicted|,|observed|,1e-30)`.
  No existe threshold cuantitativo aprobado para este cierre y no se inventó
  uno; estos diagnósticos no convierten C3 en PASS.

## Decisión

`P4_SCI_C3_INCONCLUSIVE`. El auditor clasifica automáticamente: no contiene
un PASS codificado. Al quedar C3 inconcluso, E13 no se ejecutó ni se aplicó a
G2; no hubo una nueva campaña. La propuesta E13-R1 conserva la aprobación
humana documentada de A–J, pero su evaluación sigue bloqueada por el gate C3.
