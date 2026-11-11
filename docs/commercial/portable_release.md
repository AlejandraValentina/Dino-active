# Dino Commercial - release portable

Fecha: 2026-11-11. Aplica a CP2 y no modifica contratos científicos.

## Formato elegido

El release Windows de CP2 es un **ZIP portable**. No requiere instalador ni
escribe claves de registro. El usuario descomprime en una carpeta propia y
ejecuta `Dino2T.exe`; el Worker se resuelve desde el mismo árbol `onedir`.

- Desinstalar = cerrar Dino y eliminar la carpeta descomprimida.
- Los proyectos, resultados y artefactos del usuario viven fuera de esa
  carpeta y no se eliminan al desinstalar.
- No hay servicio, tarea programada ni auto-arranque.
- El paquete incluye `build.json`, avisos de terceros y `Licencias/`.

## Integridad

Cada candidato publica:

- nombre del ZIP y SHA-256;
- SHA-256 de `Dino2T.exe` y `MotorSimWorker.exe`;
- commit fuente limpio y `build.json` embebido.

El receptor debe verificar los hashes antes de usar el paquete. Un candidato no
se reconstruye sobre otro: cada build usa un directorio nuevo.

## Aceptación mínima

1. ZIP generado desde árbol limpio con `packaged_inputs_clean=true`.
2. Storage preflight PASS.
3. Aceptación empaquetada de los flujos soportados.
4. Sin workers huérfanos al cerrar.
5. Receipt y hashes copiados a `results/commercial-product-v1/windows-*/`.

## Fuera de alcance

- Firma Authenticode, instalador MSI/Inno Setup y actualización automática.
- Licenciamiento/activación: decisión del dueño, pendiente para CP2.
