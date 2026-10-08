## Decisiones
Continuación de archivos físicos: example_file_project reutiliza la fábrica previa
y cambia solo identificación a los textos exactos solicitados; las variantes
conservan el nombre de referencia para diferir únicamente en compresión.
tools/generate_example_projects.py valida los cuatro antes de escribir, usando
save_project. El empaquetado verifica equivalencia y copia los JSON versionados.
El menú Cargar ejemplo previo se conserva; no se añade otro menú redundante.
Un módulo común llama geometry() canónico de cada ciclo; replace cambia solo
identificación descriptiva y compresión para las variantes8.2. El menú y los JSON
incluidos en el paquete usan ese módulo. No se editan constantes científicas.
La carga reutiliza _can_leave y _activate; termina sin ruta y con cambios pendientes.
Selecciona proyecto actual como origen de la próxima simulación, conservando
resultados históricos y el proceso activo. No depende de archivos externos.
## Comprobación
Pruebas de valores/protecciones/persistencia/entradas y comparación con fixtures;
recorrido Windows del EXE y resultados existentes, sin integraciones nuevas.
Revisión puntual, rc4 desde commit limpio, evidencia separada de aceptación manual.
