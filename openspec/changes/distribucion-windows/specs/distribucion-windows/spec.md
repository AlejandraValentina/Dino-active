## ADDED Requirements
### Requirement: Distribución autocontenida identificable
El sistema SHALL distribuir Windows x64 onedir con GUI sin consola y worker con
canales estándar, misma física y JSON v6, versión candidata y commit fuente limpio.
SHALL incluir recursos, ayuda, ejemplos sintéticos, licencias y receta fijada.
#### Scenario: Extracción y traslado
- **WHEN** se extrae y abre MotorSim.exe en ruta Unicode con cwd distinto
- **THEN** funciona sin repositorio, Python externo ni escribir datos en el paquete.
### Requirement: Cálculo y errores preservados
El sistema SHALL seleccionar el worker absoluto del paquete o Python en fuentes,
conservar QProcess asíncrono único, progreso, cancelación/cierre y errores visibles.
SHALL guardar diagnóstico técnico local sin red ni éxito ficticio.
#### Scenario: Auxiliar ausente o fallido
- **WHEN** no puede iniciar el auxiliar
- **THEN** informa causa, conserva estado coherente y no declara resultado exitoso.
### Requirement: Evidencia real de candidata
El sistema SHALL probar ZIP extraído, persistencia, lectores, comparación, CSV,
cancelación y Windows150, separando automatización de aceptación manual.
SHALL ejecutar solo los tres puntos autorizados y cancelaciones dentro de 300 s,
comparar con referencias sin alterar tolerancias y registrar tiempos separados.
#### Scenario: Entrega de paquete
- **WHEN** se entrega la candidata
- **THEN** informa SHA256/tamaño, rutas, versión/commit, pruebas y pendientes limpio/offline reales.
