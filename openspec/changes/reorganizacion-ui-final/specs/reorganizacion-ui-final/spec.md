## ADDED Requirements
### Requirement: Navegación por tareas
El sistema SHALL ofrecer navegación persistente Resumen, Geometría, Motor2T o
Motor4T según ciclo, Simulación, Resultados, Comparar y Datos externos.
SHALL conservar borradores, cambios pendientes y cálculo activo al navegar.
#### Scenario: Cambio de ciclo
- **WHEN** se alterna 2T/4T
- **THEN** solo su workspace queda utilizable y los datos de ambos se conservan.
### Requirement: Configuración contextual
El sistema SHALL presentar resumen real con estado de ejecutabilidad y accesos
a secciones con errores, edición común y geometría junto a sus gráficos, y
configuración específica/ conductos agrupados por ciclo con contexto existente.
#### Scenario: Datos incompletos
- **WHEN** faltan entradas admitidas
- **THEN** no inventa valores y dirige a la sección que necesita atención.
### Requirement: Ejecución y análisis separados
El sistema SHALL jerarquizar configuración/acciones/progreso/resultado de simulación;
SHALL integrar lectura de resultados, series, comparación y externos como workspaces,
sin modificar reglas, contratos ni física y sin recalcular para consultar archivos.
#### Scenario: Consulta durante edición
- **WHEN** cambia el proyecto tras abrir un resultado
- **THEN** conserva resultado/procedencia y muestra el aviso existente de configuración anterior.
### Requirement: Acceso y distribución
El sistema SHALL conservar título nativo, menú real, toolbar Nuevo/Abrir/Guardar,
barra de estado real, foco y acceso por teclado/scroll en tamaños compactos.
SHALL comprobar Windows multiescala y paquete identificado sin sobrescribir candidatos.
#### Scenario: Verificación final
- **WHEN** se entrega el rediseño
- **THEN** registra suite, revisión, capturas reales, candidata y pendientes separados de aceptación manual.
