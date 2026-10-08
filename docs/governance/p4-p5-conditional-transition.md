# Decisión de governance: transición condicional P4 → P5

Base: `3a951e0`.

P4 permanece **BLOCKED** y `NOT_GRANTED`: su clasificación científica es `P4_FINAL_BLOCKED_C3_INCONCLUSIVE`. No se reinterpreta como PASS. G2 E13-R1 sigue sin convergencia, y no hay aceptación experimental ni revisión independiente cerrada.

La decisión humana autoriza P5 como `AUTHORIZED_CONDITIONAL`, con dependencia `P4_UNRESOLVED`. Esto permite desarrollar componentes propios sin declarar verificado el núcleo P4. La transición es `PHASE CONDITIONALLY BYPASSED FOR DEVELOPMENT`.

El scope reconstruido de P5 es intake + transfers 1D: geometría/malla, solver 1D reutilizable, fixtures aislados, coupling tests, fronteras, conservación, admisibilidad, backflow, topología y su interacción declarada con cárter/cilindro. No incluye P6+.

`INDEPENDENT_OF_P4`: geometría/malla, solver 1D aislado, fixtures, conservación, admisibilidad, backflow y topología intake/transfers. `CONDITIONAL_ON_P4`: cualquier evidencia que requiera mecanismos gasdinámicos integrados o una conclusión de P4.

P5 podrá registrarse como `P5_IMPLEMENTATION_VERIFIED_CONDITIONAL`, pero no como `P5_FULLY_ACCEPTED` mientras P4 siga bloqueado. Si P4 cambia, se deben revisar los gates P5 condicionados.


## Addendum 2026-09-29

P4 fue cerrado técnicamente como `P4_PASS` con G2-v2. La revalidación posterior registró P5, P6, P7 y P8 sobre esta base en `results/p5-p8-revalidation-20260929/`. Se conservan las etiquetas `*_VERIFIED_CONDITIONAL` por trazabilidad contractual y porque la revisión independiente sigue pendiente; no equivalen a validación experimental. P9 permanece detenido y no autorizado.
