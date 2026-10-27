# Segunda ventana88: recuperación exacta y cuatro ciclos máximo

2026-10-27. La primera ventana reduce máximo19.85→3.03 y p905.22→.90, sin
estancamiento sostenido ni defecto demostrado. Persisten77 observables y deriva
de llenado/trabajo. Continuar sólo el mismo88, sin176 y sin cambiar formulaciones.

## Recuperación

Misma configuración/identidad y detector. Restaurar nativo35 y detector relativo5
con hashes verificados; reconstruir sus observaciones desde34/35 sin integrarlos.
El FAST12814°/parcial36 **no** es restore nativo. Reproducir únicamente el prefijo
parcial36 desde35: cada propuesta rechazada, paso aceptado y FAST completo deben
coincidir exactamente antes de superar el estado ya calculado. Conservar el
parcial y los ciclos31–35 originales; no recalcularlos. Esta reproducción del
prefijo es necesaria por el tipo FAST, no una nueva inicialización.

## Límite y medidas

Una invocación, máximo ciclos absolutos36–39 (relativos6–9), incluyendo
recuperación del prefijo.220s solver/240s admisión/250s watchdog;16MiB con
reserva2GiB. Separar tiempo de replay como subconjunto del solver. No usar pasos
mayores, otra CFL o tolerancias para cumplir presupuesto.

Guardar checkpoints, detector, receta y fases30° por ciclo. Seguir composición,
masa/energía del escape y cilindro, aire a300°, calor, combustible y trabajo.
Continuar los índices relativos existentes, sin resetear detector ni reloj.
Misma parada de recursos por dos transiciones consecutivas sin mejora de p90
y reducción5% del máximo; usar historia anterior para detectar estancamiento.

Ante mismatch del prefijo, inadmisibilidad o conservación: parar antes de avanzar
fuera del prefijo y diagnosticar. Ante candidato periódico: parar y preparar
auditoría; no declararlo L2 desde checkpoints. Si termina presupuesto, analizar
sin otra extensión automática. No campaña ni nueva malla por este protocolo.
