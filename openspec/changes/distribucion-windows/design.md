## Decisiones
Versión candidata 0.1.0-rc1, independiente de JSON v6 y modelos/resultados existentes.
PyInstaller onedir Windows x64: dos entradas mínimas, MotorSim.exe windowed y
MotorSimWorker.exe console para stdin/stdout; un COLLECT con dependencias compartidas.
El worker reutiliza reference_run y no importa Qt. Selector pequeño de comando
según frozen, ruta absoluta desde sys.executable; en fuentes conserva Python -m.
Recursos junto al módulo; ayuda/ejemplos generados desde referencias existentes.
Resultados permanecen en LOCALAPPDATA/MotorSim/Resultados, diagnóstico en Diagnostico;
proyectos/importaciones/exportaciones en destinos elegidos. Sin escrituras en paquete.
Acerca de expone versión y build.json generado desde commit limpio antes de construir.
Receta sin limpiezas destructivas: cada construcción ocupa un directorio nuevo.
Dependencias de construcción fijadas; licencias/avisos redistribuidos incluidos.

## Comprobación
Pruebas unitarias de arranque/errores/recursos, suite de regresión sin campañas ocultas,
una revisión puntual. ZIP extraído fuera del repositorio en ruta Unicode/con espacios,
cwd distinto, sin PYTHONPATH/VIRTUAL_ENV y sin Python externo usado por GUI/worker.
Automatización externa del ejecutable y capturas Windows/150 % y compacto;
no incorporar instrumentación al producto. Lectura/CSV con evidencia histórica.
Tres integraciones: referencia 2T B100/3000 y barrido proyecto exacto S4T B100/2500,
3000. Mismos estados, límites y comparación exacta con evidencia existente; reloj
separado de identidad numérica. Cancelaciones breves; total <=300 s incluyendo
cualquier repetición justificada por defecto de empaquetado. No repetir estudios R2.
Si no hay equipo limpio u offline aislado, registrar esos pendientes sin impedir ZIP
candidato; nunca desconectar sesión ni alterar políticas. Manual/experimental separados.
Commit fuente antes de construir paquete final; evidencia posterior en otro commit.

## Hardening autorizado posterior a rc1
Preservar binarios y evidencia rc1. Los nuevos resultados v1–v4 registran el campo
opcional timings ya admitido por el lector; no cambia versión ni física y abrir
históricos no escribe. GUI añade tiempo percibido solo al resultado confirmado
de su ejecución. Parada forzada conserva diagnóstico local con el mecanismo existente.
rc2 desde commit limpio; una reproducción focalizada (consumida) y solo un punto
B100/3000 por ciclo desde paquete final. Sin nuevas campañas ni archivo del cambio.
