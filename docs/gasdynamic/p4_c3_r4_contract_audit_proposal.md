# PROPOSAL / NOT APPROVED / NO CONTRACT CHANGE

## Auditoría focal de C3 — R4

Fecha: 2026-09-28  
Base auditada: `fd5ff9e`  
Alcance: lectura de los documentos C3 indicados, `p4_c3_return_audit.py`,
`dev_orchestrator/p4_sci_04b.py` y los artefactos R3. No se ejecutó el solver ni
una campaña.

## Dictamen

C3 sigue **INCONCLUSIVE**. Esta propuesta no autoriza una nueva corrida, no
adopta un contrato ni cambia `tasks.md`, OpenSpec o los artefactos de resultados.
E13/P9 permanecen sin cambio.

C3 contiene dos verificaciones distintas:

* **A — referencia de retorno:** comprobar, en el snapshot causal preregistrado,
  el flujo HLLC frente a ExactRiemann usando exactamente los mismos estados de
  cara reconstruidos. Así se aísla el solver de Riemann y se mide discrepancia
  de modelo numérico, no cierre de la actualización discreta. En el snapshot
  seleccionado, la cara izquierda reconstruida coincide con la celda; la pared
  no coincide, por lo que no es válido sustituir allí el estado reconstruido por
  el estado de celda.
* **B — balance de momento:** comprobar que el cambio de momento almacenado en el
  volumen de control coincide con los flujos de momento y la fuente geométrica
  que realmente definen el update productivo, en ambas etapas SSPRK2. Esto mide
  identidad de conservación discreta, pero debe auditarse por capas separadas.

El auditor R3 mezcla esos objetivos en B. `_recompute_stage` usa ExactRiemann
en la interfaz y en la pared, mientras `p4_sci_04b.py` actualiza con HLLC. Además,
el productor usa estados reconstruidos (`lf[0]` y `rf[-1]`) y el auditor usa los
estados de celda (`primitive[0]` y `primitive[-1]`). Por ello
`max_abs_residual=5.840234051652552e-06` no es una medida pura de cierre
discreto HLLC.

Esto no demuestra que el residuo sea inválido como diagnóstico de la comparación
que efectivamente se hizo; demuestra que no puede interpretarse como verificación
de la identidad del update productivo.

## Evidencia cuantitativa offline

El snapshot seleccionado conserva estados y permite recalcular un punto sin
avanzar la solución. En `sample_time_pre_step = 0.0026532366020821743 s`:

| término de momento integrado | auditor Exact/celda | HLLC con estado productivo | diferencia |
|---|---:|---:|---:|
| cara izquierda | 38.96076990845837 N | 38.96090451400843 N | +1.3460555006616914e-04 N |
| pared | 46.55101699696457 N | 46.60017727523689 N | +4.916027827231785e-02 N |

El efecto combinado sobre el incremento SSPRK2 de ese paso es
`-2.8187660724276252e-08 kg*m/s`. La mayor parte de la diferencia de pared
no es únicamente HLLC-vs-Exact: el estado reconstruido productivo tiene
`u=-7.696712366983549e-05 m/s`, mientras el auditor usa la celda con
`u=-0.2807982084376723 m/s`. Manteniendo los mismos estados de celda, la
diferencia HLLC-vs-Exact es `+1.3460555006616914e-04 N` en la izquierda y
`-2.2596389030127284e-05 N` en la pared.

No es posible descomponer offline el máximo global `5.840234051652552e-06`
fila por fila con los dos artefactos pedidos: el JSON de momento conserva
1,940 residuos y términos ya reconstruidos, pero no conserva para cada fila
los estados primitivos/reconstruidos necesarios para reevaluar HLLC y Exact
con las mismas entradas. Por tanto no se atribuye ese máximo a HLLC, Exact o
reconstrucción sin evidencia adicional.

## Qué debería demostrar B por capas

B debe distinguir explícitamente estas capas, por etapa:

* **B0 — inputs de estado de cara:** obtener o recibir los estados pre-step
  reconstruidos de las caras auditadas, además del ghost de pared cuando
  corresponda. B0 verifica por separado que esos inputs representan la
  reconstrucción declarada; no calcula ni valida todavía el flujo HLLC.
* **B1 — HLLC independiente:** evaluar HLLC sobre exactamente los estados de
  cara de B0, para la interfaz y la pared, en una ruta auditora independiente.
  B1 jamás lee `interface_flux_observed` ni ningún flujo u otro output calculado
  por el operador productivo.
* **B2 — balance SSPRK2:** combinar los flujos producidos por B1 con el mismo
  volumen, áreas, fuente `p_i (A_{i+1}-A_i)`, signos, `dt`, momento almacenado
  antes/después y orden de las dos etapas SSPRK2. B2 comprueba el balance; no
  vuelve a reconstruir estados ni sustituye los flujos de B1 por outputs
  productivos.

Para B0 hay dos opciones válidas y mutuamente excluyentes de implementación:

1. una reconstrucción externa independiente mínima, limitada a las caras
   auditadas; o
2. persistir los estados de cara productivos como inputs y verificar su
   reconstrucción mediante un subgate separado.

En ambos casos B1 debe consumir esos estados explícitos y jamás leer outputs de
flujo productivos. Compartir una definición abstracta de reconstrucción no basta
ni sustituye esta separación de inputs, ruta HLLC y outputs. “Independiente” no
exige un tercer modelo físico: exige una segunda evaluación del mismo contrato
numérico. EOS y geometría pueden ser comunes; la evaluación HLLC y sus entradas
deben quedar separadas. ExactRiemann queda reservado para A y como diagnóstico
comparativo.

## Siguiente paso propuesto, sin cambiar la física

1. Fijar B0 mediante una de sus dos opciones válidas: instrumentación durable
   de estados de cara reconstruidos por etapa, o reconstrucción externa mínima.
   En ambos casos conservar también ghost de pared, `dt`, áreas, fuente y
   momento antes/después. Esto no cambia el solver.
2. Implementar B1 como evaluación HLLC independiente sobre los inputs B0 para
   interfaz y pared. Calcular B2 desde esos resultados y los estados almacenados,
   no desde campos productivos.
3. Probar la separación con: (a) paridad B1 contra una tabla congelada de
   microestados HLLC, (b) mutación controlada de un flujo productivo que no
   cambie B1/B2, y (c) comparación de entradas y salidas sin aliasing ni lectura
   de nombres de campos productivos. Verificar B0 con su subgate propio.
4. Mantener A separado: ExactRiemann y HLLC sobre los mismos estados de cara
   reconstruidos, con la selección causal de snapshot ya fijada.

La parte objetiva de B puede ser una consistencia discreta con una política
preregistrada de redondeo, backward-error y/o ULP, incluyendo identidad de
inputs, signos, etapas y orden de redondeo documentado. Esa política no es un
threshold físico calibrado al resultado observado. A, en cambio, todavía
requiere un criterio científico preregistrado —benchmark y/o refinamiento— con
reglas fijadas antes de observar resultados; no se puede introducir un threshold
post-hoc.

## Criterio preregistrable alternativo

Antes de cualquier nueva ejecución, registrar por separado: (i) para A, un
benchmark HLLC-vs-Exact y/o estudio de refinamiento con reglas de fallo fijadas
antes de observar resultados; y (ii) para B, identidad discreta HLLC en un
conjunto de microcasos y en el fixture C3 a varias etapas, con política de
redondeo/backward-error/ULP preregistrada. Un estudio de refinamiento del
residuo B puede ser diagnóstico adicional, pero no reemplaza B0/B1/B2. La
elección pertenece al gate humano; esta propuesta no adopta un threshold físico
ni autoriza ejecución.

Este documento no modifica `tasks.md`, OpenSpec, contratos aprobados ni
artefactos de resultados. C3 sigue INCONCLUSIVE y E13/P9 siguen sin cambio; es
una propuesta de siguiente paso solamente, sin autorización de nueva corrida ni
de contrato.
