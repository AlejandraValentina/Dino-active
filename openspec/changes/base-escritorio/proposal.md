# MotorSim v0.1 — Base de escritorio

Estado: definición preparada; implementación no iniciada. Esta actualización
organiza la documentación y no constituye una orden para desarrollar la aplicación.

## Why

Obtener una base de escritorio utilizable antes de abordar un simulador de motores.
El recorrido de esta entrega es crear, editar, guardar y recuperar un proyecto;
no se intenta resolver ahora el funcionamiento físico de motores 2T o 4T.

## What Changes

- Una ventana en español con nombre de proyecto y selector 2T/4T.
- Operaciones Nuevo, Abrir, Guardar, Guardar como y Salir.
- Archivos JSON locales y protección frente a pérdida de cambios.
- Pruebas focalizadas e instrucciones de ejecución comprobadas.

El comportamiento exacto y las comprobaciones están únicamente en
[la especificación](specs/gestion-proyectos/spec.md). El diseño y las tareas
no pueden añadir requisitos funcionales fuera de ella.

## Capabilities

### New Capabilities

- `gestion-proyectos`: edición y persistencia de la identificación de un proyecto
  de motor, con protección del trabajo del usuario.

### Modified Capabilities

Ninguna. No existe una aplicación implementada ni una capacidad consolidada.

## Impact

La futura implementación añadirá código Python, dependencias mínimas y pruebas.
No incorpora código, contratos o infraestructura de Dyn2T/Dino2Next. No crea
servidor, base de datos, instalador, orquestador externo ni equipo multiagente.

## Procedencia y reconciliación documental

Se respeta el estado de `main` en `d021a6715bb5b9edee9a12588fc7cc27d04016f7`.
Ese commit retiró `doc/ALCANCE_0_1.md` y `doc/README.md`, que incluían una variante
con geometría. No se restauran esos archivos ni se reincorporan sus funciones.
La base conserva el alcance de `docs/ALCANCE_INICIAL.md`: nombre, tipo y archivos,
sin dimensiones ni cálculos. Se precisan valores iniciales y formato de archivo.

El documento de alcance anterior pasa a ser una referencia a OpenSpec para no
mantener dos fuentes de requisitos. Su texto original permanece en el historial
Git. La indicación de simulación no disponible sigue siendo obligatoria.

## Límite y cierre

Fuera de esta entrega: parámetros físicos, geometría, cilindrada, presión,
temperatura, combustión, intercambio de gases, ondas, par, potencia, RPM,
gráficas, CAD, optimización, cuentas, sincronización, plugins y solvers futuros.

El código solo comienza mediante una solicitud explícita de implementación.
Termina al comprobar la especificación y las tareas; no habilita la etapa física.
Una comprobación pendiente se informa como pendiente, no como aprobación.
