# Recuperación del contrato del diagnóstico, sin nueva simulación

2026-10-27. Las cuatro auditorías numéricas27–30 pasaron y reprodujeron estado,
reloj, eventos y balances. El intento original terminó STOPPED porque el nuevo
wrapper etiquetó las observaciones de datos como REFERENCE_PERIODIC_CONVERGENCE_V2.
El contrato documentado de compare_cycles_v2 exige datos V1; V2 versiona el
detector y la semántica de trabajo firmado. El comparador rechazó correctamente
la etiqueta incorrecta. No se demostró una discrepancia física.

Corrección exclusiva del wrapper: conservar primary['contract']; rechazar
contratos desconocidos. Test reproduce INVALID con etiqueta V2 y PASS con el
contrato V1 original. No se modifican productor, auditor, detector, controles,
umbrales ni solver; no se reetiquetan los archivos de primarias originales.

Preservar intento fallido y sus hashes en manifest-original.json. Verificar
compressed_sha256 y primary_sha256 canónico de las cuatro primarias auditadas;
reutilizar prefix1–26 del receipt original ligado por hash. Reconstruir
detector con observables de esas primarias, sin engine.step ni auditar otra vez.

Presupuesto120s watchdog,90s admisión de lecturas;128MiB temporales y4MiB
receipt con preflight/reserva2GiB. Es una recuperación de datos, no extensión
de ciclos ni de la campaña. Sólo declarar PASS si el detector intacto devuelve
PERIOD_1/converged_cycle30. Conservar también un posible resultado desfavorable.
