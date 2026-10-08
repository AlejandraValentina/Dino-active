## Context

Ver [la propuesta](proposal.md). El repositorio todavía no contiene la aplicación.
Los requisitos observables están en [gestion-proyectos](specs/gestion-proyectos/spec.md).

## Goals / Non-Goals

Diseñar una base pequeña que pueda probarse sin depender de una ventana para
cada comprobación. No diseñar un marco general de simulación ni decidir ahora
los modelos físicos. OpenSpec organiza el desarrollo; no se ejecuta con MotorSim.

## Decisions

- Usar Python, PySide6/Qt Widgets y biblioteca estándar. Registrar las versiones
  realmente probadas. No añadir bibliotecas numéricas o de gráficos para este cambio.
- Separar datos y validación, persistencia e interfaz mediante
  pocos módulos. Codex decide nombres y carpetas; no se exige una jerarquía de capas.
- Mantener un borrador editable que pueda estar incompleto. Validarlo al guardar;
  validar los datos de un archivo antes de sustituir el proyecto activo.
- Representar por separado datos, ruta activa y cambios pendientes. Cancelar un
  diálogo o fallar una operación no confirma una transición de proyecto.
- Escribir primero un archivo temporal junto al destino y reemplazarlo únicamente
  después de completar la escritura; cerrar los manejadores antes del reemplazo.
  También puede utilizarse una primitiva equivalente de Qt. No marcar como guardado
  ni cambiar la ruta activa si falla. No se promete durabilidad absoluta ante corte
  de energía: no se agrega infraestructura de recuperación o journaling.
- Usar controles estándar y una ventana redimensionable. No incorporar temas,
  paneles o botones para funciones que no están implementadas.
- Ejecutar desde un entorno Python local. El empaquetado queda fuera del cambio.

## Risks / Trade-offs

- Un entorno sin escritorio Windows no verifica la experiencia real: separar
  pruebas automatizadas y prueba manual; dejar pendiente lo no ejecutado.
- Los diálogos de archivo pueden fallar o cancelarse: resolver esas rutas antes
  de reemplazar datos o descartar cambios.
- La selección 2T/4T no valida un simulador: no presentarla como tal.
- La integración de OpenSpec puede necesitar instalación en el entorno de Codex:
  la preparación está en el README. Un fallo de entorno no justifica rediseñar
  la aplicación ni repetir indefinidamente la misma operación.
