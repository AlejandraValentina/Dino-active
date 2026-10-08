## ADDED Requirements
### Requirement: Jerarquía y navegación coherentes
El sistema SHALL mantener navegación permanente por tareas, ciclo inactivo oculto,
foco/hover/selección visibles y encabezados con propósito en los ocho workspaces.
SHALL conservar acciones, estado nativo y datos/borradores al navegar.
#### Scenario: Edición y navegación
- **WHEN** se alterna entre configuración y análisis
- **THEN** conserva datos, dirty y ejecución activa sin lanzar cálculos inesperados.
### Requirement: Portada y configuración contextual
Resumen SHALL separar identidad, geometría esencial, preparación y acciones reales.
Geometría SHALL reunir formulario, derivados y visualización. Motor2T/4T SHALL
agrupar sus editores/curvas y contexto vigente sin datos del otro ciclo.
#### Scenario: Preparación incompleta
- **WHEN** faltan entradas
- **THEN** informa su estado y dirige a secciones concretas, sin inventar resultados.
### Requirement: Cálculo y análisis guiados
Simulación SHALL separar preparación/validación/acciones de progreso y resultados.
Resultados SHALL ofrecer estados vacíos útiles, lectura y puntos de barrido;
Comparar SHALL identificar A/B y compatibilidad junto a tablas/curvas.
Datos externos SHALL presentar cuatro bloques: importación, serie, contraste y
exportación; exportar solo con contraste válido, con metodología compacta.
#### Scenario: Datos externos vacíos
- **WHEN** no hay importación ni serie
- **THEN** orienta a importar y mantiene resultados/exportación sin datos ficticios.
### Requirement: Compatibilidad y comprobación
El sistema SHALL preservar contratos, física, modelos, worker y persistencia.
SHALL adaptar columnas a ancho compacto, conservar teclado/scroll y registrar
pruebas, revisión independiente, capturas Windows multiescala y EXE identificado.
#### Scenario: Entrega de candidata
- **WHEN** se construye la rc4 refinada
- **THEN** conserva anteriores y diferencia evidencia automática/visual de aceptación manual pendiente.
