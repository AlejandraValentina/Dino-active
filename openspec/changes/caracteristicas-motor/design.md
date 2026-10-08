## Context

Se amplía la implementación local y su rediseño sin reemplazarlos desde el remoto.
Los requisitos están en specs/ficha-motor/spec.md; base-escritorio conserva su
historial y su recorrido manual pendiente.

## Decisions

- Mantener los módulos actuales. Datos y parseo numérico fuera de los widgets.
- Usar entradas de texto para distinguir vacío, dato válido y error; aceptar coma
  o punto decimal (también notación científica), nunca agrupación de miles.
  Cilindros acepta dígitos enteros positivos. No bloquear la edición incompleta.
- Nuevos textos: cadena vacía cuando no se informan. Nuevos números: null cuando
  no se informan. Los errores visibles bloquean guardar y nunca se convierten en null.
- JSON plano versión 2: format_version, name, cycle, manufacturer, model,
  cylinder_count, bore_mm, stroke_mm, rod_length_mm, compression_ratio, notes.
  Todas las claves se escriben y son obligatorias al leer versión 2. Los números
  son números JSON; no se guardan resultados derivados ni unidades en sus valores.
- Lectura directa de versión 1: conservar name/cycle, inicializar los nuevos campos
  vacíos/null. Solo el siguiente guardado explícito escribe versión 2.
- Conservar escritura temporal junto al destino y reemplazo seguro. Se valida
  antes de sustituir el proyecto activo, incluida toda la ficha.
- Cálculo geométrico con biblioteca estándar; resultados con dos decimales, sin
  redondear las entradas guardadas. Separar dependencias: D/S para cilindrada por
  cilindro y D/S/N para total. Biela y compresión no intervienen en esos resultados.
- Dos grupos lado a lado con ancho suficiente, apilados en ventanas estrechas,
  con desplazamiento vertical y orden de foco coherente. Selector 2T/4T compacto.

## Risks / Trade-offs

La comprobación de Windows y escalado se registra separada de tests sin pantalla.
El campo incompleto puede guardarse; el inválido requiere corrección. No se
construye un sistema general de migraciones ni se habilita simulación física.
