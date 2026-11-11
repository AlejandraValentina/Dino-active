# Arquitectura y hoja de ruta del frontend

Evaluación técnica sobre `696b8fc`, con comprobación del código y de la aplicación
real. Es una SELF_REVIEW; no se presenta como revisión de un agente independiente.
El alcance de cierre es F0 (integridad) + F1 (recorrido coherente en fuente).
Las capacidades avanzadas siguientes requieren fases propias.

## Decisión y fundamentos

Conservar Qt Widgets y los adaptadores científicos existentes. La duplicación
de contextos, las notificaciones indiscriminadas y los comandos sin frontera de
edición explican mejor los defectos que el toolkit. Reescribir en web agregaría
otro protocolo de ejecución, persistencia y empaquetado sin resolver esas causas.
Unificar los solvers o imponerles el mismo ciclo de vida sería incorrecto.

La separación propuesta tiene cuatro responsabilidades:

1. Contextos de documento: identidad, variante, historial y persistencia.
2. Borradores de edición: texto local, validación y aplicar/descartar/cancelar.
3. Servicios de aplicación: preparación de corridas y cierre portable de archivos.
4. Presentación: cabecera, componentes, preparación y resultados por familia.

`WorkspaceExperience` reúne presentación común y resolución de borradores del
shell. No calcula física ni sustituye los contextos. `native_parameter_form`
presenta magnitudes físicas sobre las celdas exactas del editor existente; la
precisión original permanece intacta hasta editar. `portable_artifacts` reúne
dependencias sin reescribir manifiestos científicos. El historial de corridas
existente continúa siendo el explorador 2T; el acceso común muestra referencias
vinculadas sin depender de que su índice asíncrono ya haya terminado.

Qt describe el envío manual y la reversión como una forma de mantener cambios
locales hasta confirmarlos ([QDataWidgetMapper](https://doc.qt.io/qtforpython-6.10/PySide6/QtWidgets/QDataWidgetMapper.html)).
Se adopta ese principio, conservando el editor actual para evitar una migración
de modelo de datos en el mismo cambio. La documentación de guardado atómico de
Qt también separa escritura temporal y publicación final ([QSaveFile](https://doc.qt.io/qt-6/qsavefile.html));
Dino conserva su persistencia Python existente y prepara importaciones en una
carpeta temporal propia antes de publicarlas.

En simulación profesional resulta útil separar definición, estudio y resultados;
es la organización documentada por [COMSOL Model Builder](https://www.comsol.com/comsol-multiphysics/model-builder).
La inferencia para Dino es mantener MODELO → SIMULAR → RESULTADOS con contexto
persistente, sin copiar su complejidad ni atribuir equivalencia de capacidades.

## Contratos de interacción de F1

- La cabecera identifica proyecto, motor, familia, variante, hash aplicado y
  borrador/cambios sin guardar. El hash es identidad de configuración, no número
  de versión comercial ni evidencia física. Las salidas no cambian esa identidad.
- 2T, 4T nativo y referencia 0D permanecen separados. La referencia no repite las
  acciones globales. El asistente de creación declara los tres modelos.
- El editor nativo ofrece componentes con unidades, fuentes, nombres accesibles
  y ayuda de valor exacto. Avanzado conserva acceso al esquema. Cambios ajenos a
  la edición no reconstruyen un borrador pendiente.
- Aplicar toda la referencia es transaccional: un campo inválido restaura el
  documento y su historial, conservando el texto para corregirlo.
- La preparación muestra número de RPM y presupuesto agregado cuando existe.
  Presupuesto no significa duración garantizada. La corrida nativa identifica
  configuración enviada y bloquea edición/variantes hasta terminar.
- Una corrida 2T nueva vincula su resultado al proyecto de origen y ofrece
  acceso directo. Los resultados externos abiertos sin vínculo no se incluyen
  por el mero hecho de estar en pantalla.
- La comparación nativa anticipa elegibilidad con el contrato actual y vuelve
  a verificar al calcular/exportar. Integridad no implica periodicidad, y ninguna
  de ellas implica validación experimental.
- Contenido portable muestra cantidad/tamaño de archivos, ausencias y alcance;
  exportación e importación notifican parcialidad y legacy por separado.
- Ayuda con fondo/texto explícitos, foco visible y comprobación del contexto
  activo. No se declara accesibilidad completa por añadir nombres accesibles.

## Trazabilidad de los 23 hallazgos

“Cubierto” significa alcance implementado de F0/F1; su aceptación depende del
recibo de verificación. “Parcial” mantiene una obligación visible para otra fase.

| Hallazgo | F0/F1 | Trabajo siguiente / criterio |
|---|---|---|
| UX-001 P0 | Cubierto: frontera de borrador, conservación y bloqueo nativo | Mantener negativos en cada cambio de comandos |
| UX-002 P0 | Cubierto: cierre transitivo, bytes inmutables y parcialidad | Aceptación del candidato empaquetado |
| UX-003 P0 | Cubierto: Path y fallo visible con dirty intacto | UAT de permisos del entorno destino |
| UX-004 P1 | Cubierto: cabecera en todos los modos/familias | UAT con proyectos de nombres largos |
| UX-005 P1 | Cubierto: navegación común de referencia | Mantener acciones de familia explícitas |
| UX-006 P1 | Cubierto: formulario físico y esquema avanzado | Restricciones y ayuda más detalladas por campo |
| UX-007 P1 | Cubierto para conversiones: componente, foco y borrador intacto | Mapear errores complejos de contrato a todos los campos |
| UX-008 P1 | Cubierto: contraste de ayuda | Medición formal de contraste y alto contraste Windows |
| UX-009 P1 | Cubierto: primeros pasos del contexto activo | UAT con proyectos importados |
| UX-010 P1 | Cubierto: acceso al resultado terminal 2T | Mantener indicador ante cambio de proyecto |
| UX-011 P1 | Parcial: vinculación automática de corridas nuevas y vista portable | Vincular resultados externos explícitamente con revisión de identidad |
| UX-012 P1 | Parcial: planes y presupuestos visibles por familia | Preparador común con capacidades, sin igualar contratos |
| UX-013 P1 | Alcance de cola 0D explícito; cola universal pendiente | F2: JobManager con snapshots, cancelación y persistencia por adaptador |
| UX-014 P1 | Parcial: preflight nativo y guía existente | Selector común de pares y diferencias de diseño en 2T |
| UX-015 P2 | Pendiente | F3: esquema coordinado con selección; nunca geometría inventada |
| UX-016 P2 | Pendiente | F3: zoom, cursor y tabla de muestras enlazada, con unidades |
| UX-017 P2 | Parcial: estados separados en cabecera/corridas/bundle | Catálogo común de términos y unidades por adaptador |
| UX-018 P2 | Parcial: formularios desplazables y capturas de tamaños | F2: redistribución completa; no prometer soporte de toda resolución |
| UX-019 P2 | Pendiente | F2: selector de recuperaciones con identidad/fecha y abrir copia |
| UX-020 P2 | PENDING_UAT | F2: teclado, lector de pantalla, escalado y alto contraste con usuarios |
| UX-021 P2 | Pendiente | F2: renombrar variantes nativas sin cambiar identidades históricas |
| UX-022 P3 | Parcial: etiquetas nuevas y modelos explícitos | F3: catálogo/encoding global sin reescribir evidencia histórica |
| UX-023 P3 | Parcial: menos navegación duplicada y contexto común | F3: avisos escalonados; preservar estados científicos esenciales |

## Orden posterior y criterios de salida

F2: comandos del shell y servicios comunes antes de un scheduler universal.
Extraer progresivamente el coordinador del shell a adaptadores tipados; añadir
vinculación externa, selector de recuperación y variantes nativas. El scheduler
debe conservar snapshots, exclusión de workers, checkpoints y estados propios
de cada familia; no implementar una cola visual que finja persistencia.
Salida: fallos/reinicio durante cada estado, roundtrip de cola y UAT accesible.

F3: explorar resultados y componentes. Usar sólo coordenadas/muestras que los
artefactos realmente contengan. Salida: selección reproducible de muestras,
unidades correctas, datos ausentes explícitos y comparaciones rechazadas sin
debilitar criterios. El diagrama es una ayuda de navegación, no CAD ni validación.

## Riesgos y límites

El coordinador común todavía conoce controles del shell: es una transición
acotada, no la arquitectura final desacoplada. Las tablas avanzadas siguen como
buffer del editor nativo; migrarlas requiere conservar precisión y provenance.
El cierre de archivos se limita a 512 MiB; estudios 2T con dependencias externas
no cubiertas se declaran parciales. La reubicación legacy no autentica su origen.
No hay cola general 2T/nativa, diagrama coordinado ni exploración gráfica avanzada
nuevos. Ninguna prueba de esta entrega acredita precisión del solver o validación
experimental. WINDOWS_ACCEPTED y UAT humano requieren aceptación propia.
