# Método, alcance y cobertura

## Revisión observada

Fecha de investigación: 11 de noviembre de 2026, America/Montevideo.
Producto: `d44305c24ec81d9b767305d319a660c0c034e5c9`, rama de origen
`feat/commercial-product-cp1`. Su historia contiene la integración de CP0,
la interfaz unificada y las seis entregas CP1. La carpeta de la conversación
estaba en una revisión CP0 anterior: no se utilizó como sujeto de la auditoría.
No se atribuyeron carencias antiguas a funciones que CP1 ya implementó.

Se creó `audit/dino-frontend-ux-v1` en un worktree independiente de E:. No se
cambió `main`, no se hizo push ni se construyó un candidato Windows. La
auditoría de regresiones CP1 y sus archivos no se modificaron. La cola operativa
de este worktree registra exclusivamente el objetivo de investigación solicitado;
conserva el objetivo anterior y los bloqueos heredados como provenance.

## Perspectiva y preguntas

Recorrido cognitivo de una persona que conoce motores, pero no el repositorio:

1. ¿Dónde creo/abro mi motor y cómo sé qué familia/núcleo estoy usando?
2. ¿Qué magnitud modifica cada control, en qué unidad y con qué procedencia?
3. ¿La configuración que veo es la que se va a guardar o ejecutar?
4. ¿Cuántos puntos voy a ejecutar, qué presupuesto tienen y cómo cancelo?
5. ¿Dónde quedó el resultado y qué puedo inferir de él?
6. ¿Qué variantes y corridas son comparables y por qué se rechaza un par?
7. ¿Puedo reabrir, recuperar y compartir mi trabajo sin perder su procedencia?

Se combinaron observación en ejecución, eventos de ratón/teclado Qt, inventarios
de widgets, lectura de código y verificación de archivos. La causa indicada en
cada hallazgo es una hipótesis sustentada en código, no una modificación aplicada.

## Entorno y aislamiento

- Windows, Python 3.11.0 x64, PySide6/Qt 6.11.2, plataforma Qt `windows`.
- La aplicación importó `motorsim` desde el worktree de auditoría. Se reutilizó
  únicamente el intérprete y dependencias fijadas de un entorno existente,
  sin instalar paquetes ni modificar ese entorno.
- Ventana real y capturas mediante `QWidget.grab()`. No fue una maqueta ni una
  ejecución `offscreen`. Pantalla disponible 1440×900; tamaños de cliente
  observados 1360×860 y 980×680, además del arranque ajustado al escritorio.
- `DINO_TEST_SETTINGS_ROOT` aisló QSettings de los ajustes del usuario.
- `DINO_ARTIFACT_ROOT` y la salida del worker 0D se aislaron en un directorio
  externo de auditoría. Se utilizó un override de LOCALAPPDATA sólo dentro del
  proceso de auditoría para la salida 0D; ninguna sesión externa heredó el cambio.
- Proyectos nuevos y copias de fixtures. El ejemplo legacy se copió antes de
  importarlo. Se preservaron los originales y las clasificaciones históricas.
- El preflight de almacenamiento aprobó una estimación de 0,1 GiB y reserva
  de 2 GiB antes de las corridas/barridos acotados. No se redujeron CFL,
  precisión ni tolerancias. No se lanzó una campaña de barrido completo.

Hubo una exploración preliminar con Qt 6.10.1. Sus capturas sin prefijo `p`
se conservan, pero **no fundamentan hallazgos**. Los recorridos utilizados
se repitieron con Qt 6.11.2. La excepción QAction observada en el entorno
preliminar no se atribuyó al producto fijado.

## Automatización y límites de la observación

`audit_tools/frontend_audit/live_driver.py` abrió `DinoDesktopWindow` sin cambiar
el código del producto. Su puente HTTP sólo escuchó en loopback y permitió
enviar eventos QTest e inspeccionar estados. Las acciones se registraron en
un journal. En operaciones de archivos se sustituyó exclusivamente la respuesta
del selector de ruta: serialización, exportación/importación y validación fueron
las reales. La creación de motor también utilizó el controlador real del diálogo.

La recuperación abrió otra instancia real del shell, con borradores reales del
servicio de autosave. Se adelantó el tick de autosave para hacer el caso
reproducible. Algunos avisos modales se aceptaron con entrada Win32 dirigida
exclusivamente al PID de auditoría cuando el callback de instrumentación no los
resolvió. No se inspeccionaron ni controlaron aplicaciones de terceros.

El cierre de limpieza encontró un aviso de cambios 0D pendientes; se cerró el
aviso y finalizó la aplicación tras registrar cero workers activos. No se presenta
esa limpieza como una aceptación adicional del cierre seguro del producto.

Se preservan también errores de instrumentación (delegado de celda destruido,
un KeyError al inspeccionar un campo y timeouts del puente durante modales).
No se cuentan como defectos de Dino. Las tres incidencias P0 se sustentan en
estados/archivos reales y código del producto, no en esos fallos del harness.

## Matriz de recorridos

| Ruta | Modalidad | Qué se observó | Evidencia primaria | Límite |
|---|---|---|---|---|
| R01 Arranque y navegación | 2T/nativo/0D | Menús, modos, componentes y estados vacíos | p01…p11 | Primera experiencia de un evaluador, no estudio con participantes |
| R02 Crear y guardar | 2T/nativo | Asistente por familia y guardado en raíz aislada | p29…p31, p14…p15 | Selector de archivo dirigido por harness |
| R03 Editar y validar | 2T/nativo | Entrada inválida, aplicar, borrador, transición a simular | p13, p26…p28, p32…p35 | No se probaron todas las combinaciones del esquema |
| R04 Undo/redo | 2T | Diámetro 56→57→56→57 mediante acciones de teclado | p33…p35 | No acredita toda la cobertura undo/redo de 4T |
| R05 Variantes | 2T/nativo | Duplicar/crear, selección y acceso a operaciones | p14, p67 | Renombrado con resultados no ejercido |
| R06 Punto real | 2T | 3000 RPM, un ciclo, presupuesto 30 s; no convergido con checkpoint | p36…p42 | Ingeniería transitoria; no prestaciones periódicas ni validación |
| R07 Punto real y borrador | Nativo | 3000 RPM, un ciclo máximo, 10 s; terminación por tiempo con cero ciclos; se comprobó config enviada | p16…p21, p26…p28 | No demuestra periodicidad ni precisión |
| R08 Curva y cancelación real | Nativo | 3000/3500 RPM, un ciclo máx., 10 s/punto; cancelar, 1/2 puntos intentados | p23…p25 | No curva completa ni reinicio exacto |
| R09 Curva RPM real y preparación | 2T | Diálogo completo y barrido real 3000/3500 RPM, un ciclo/punto, 20 s/punto y 50 s agregados; dos puntos no convergidos, curva parcial | p45, p70…p73 | No barrido de prestaciones periódicas ni campaña completa |
| R10 Curva real y preparación de cola | 0D | Paso 0 rechazado; dos RPM 3000/3500 convergidas y vinculadas; guardar/reabrir restauró la curva. Se agregó además un ítem a cola | p46…p49, p74…p76 | La cola de varios trabajos se preparó; no se ejecutó ni reanudó |
| R11 Punto real de referencia | 0D | Worker real a 3000 RPM, convergido, resultado cargado | p50…p51, p57 | Sólo referencia sintética; no valida el nativo |
| R12 Resultados y trazas | 2T/nativo/0D | Curvas vacías, transitorios, presión y resultado convergido de referencia | p20…p22, p42, p57…p59 | No se hizo evaluación de exactitud científica |
| R13 Comparación | 2T/nativo | Estado de comparación y rechazo del mismo extremo nativo | p22, p59 | No se generó un nuevo par periódico elegible |
| R14 PDF | 2T | Exportación real desde resultado no convergido, 31660 bytes | p43 y journal | Existencia/flujo probados; tipografía y multipágina no auditadas |
| R15 Bundle 2T | 2T | Exportación tras cargar corrida; manifiesto con cero resultados vinculados | p44 y journal | No se interpretó la selección como vínculo persistente |
| R16 Bundle nativo | Nativo | Exportar/importar con dos corridas: faltan dependencias; Guardar falla después | p53…p55, p66, stderr | Defecto reproducido; no reparado |
| R17 Histórico | Nativo | Copia del ejemplo Stage2 8000 RPM, aviso y clasificación legacy | p61…p62 | No promoción a integridad verificada ni comparación elegible |
| R18 Ayuda | Nativo | Apertura desde Ayuda, lectura y comprobaciones de contexto | p56 | No evaluación de toda la documentación |
| R19 Recuperación | 2T y secuencia de avisos | Borrador real, nueva instancia, copia sin ruta y hash original intacto | p65, p68 y journal | No se simuló un corte de energía/crash del sistema operativo |
| R20 Compacto y teclado | 2T/nativo | 980×680 y secuencia de doce Tab | p12, p60, p69 | Sin lector de pantalla, DPI múltiples ni alto contraste |

Los tags enlazan PNG e inventario JSON con el mismo nombre en
`results/frontend-audit-v1/captures/`. El índice incluye dimensiones, plataforma
y SHA-256. El journal, stderr y estado final están archivados en `evidence/`.

## Comparadores y criterios externos

- [COMSOL: organización del escritorio](https://www.comsol.com/support/learning-center/article/Personalize-the-desktop-34391)
  documenta árbol del modelo, ajustes de selección, gráficos y mensajes/progreso/log.
  Se toma el patrón de contexto + selección + inspector y progresión de trabajo,
  no una reproducción estética ni una comparación de precisión de solvers.
- [ANSYS Workbench: Outline](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/wb2_help/wb2h_ViewOutline.html)
  documenta resúmenes de datos por proyecto y parámetros. Se usa como criterio
  para un explorador orientado al objeto de trabajo y sus relaciones.
- [W3C: contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)
  aporta la referencia de 4,5:1 para texto normal. Se utiliza como criterio de
  diseño; no se declara certificación WCAG de una aplicación de escritorio.

Fuentes oficiales consultadas el 11 de noviembre de 2026. No se operó EngMod2T,
COMSOL ni ANSYS en esta auditoría y no se evaluó su rendimiento o exactitud.

## Qué no se acredita

- Validación experimental, calibración o precisión predictiva de ningún núcleo.
- Cierre de toda la regresión CP1 o de los contratos numéricos. No se relanzó
  la campaña de regresiones en curso; la revisión no cambia producto ni fixtures.
- UAT con preparadores de motores, lectores de pantalla o una matriz completa
  de monitores/DPI. Son verificaciones previstas en el backlog.
- Calidad de un nuevo binario: se ejecutó fuente fijada, sin reconstruir paquetes.
- Funcionamiento del prototipo HTML en navegador: el conector Browser informó
  que no había ningún navegador disponible. Se conserva el HTML como propuesta;
  los wireframes SVG sí se renderizaron e inspeccionaron visualmente.
- Implementación del rediseño: todos los ítems del backlog están propuestos,
  no activados. Las imágenes de wireframes se distinguen de las capturas reales.
