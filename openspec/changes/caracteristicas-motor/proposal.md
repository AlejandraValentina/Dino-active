## Why

Ampliar la base existente con una primera ficha editable y persistente del motor,
útil para registrar geometría y conocer su cilindrada. Implementación autorizada
por la usuaria; no implica aceptación ni cierre retrospectivo de base-escritorio.

## What Changes

- Editor «Motor» con Datos generales y Geometría, adaptable al ancho.
- Características opcionales, validación numérica y cilindrada de solo lectura.
- JSON versión 2 y lectura de versión 1 sin escritura automática.
- Se conservan acciones de archivo, guardado seguro y protección de cambios.

## Capabilities

### New Capabilities
- `ficha-motor`: datos del motor, geometría y compatibilidad de archivos.

### Modified Capabilities
Ninguna capacidad consolidada: base-escritorio permanece sin archivar.

## Impact

Cambios locales en datos, ventana, pruebas y README. Solo Python estándar y
PySide6. Sin simulador, dependencias decorativas, integración automática OpenSpec,
prompts globales, lumbreras, válvulas, conductos, combustión, potencia, par o gráficas.
