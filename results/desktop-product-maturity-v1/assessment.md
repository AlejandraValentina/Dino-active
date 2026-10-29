# Evaluación funcional Desktop — primera entrega

## Alcance y aceptación

Estado: PARCIAL. rc9 protegido se abrió e interactuó gráficamente mediante mouse y teclado Windows. La sesión se bloqueó durante el diálogo de guardado. No se afirma haber completado los diez escenarios por GUI. No se lanzó simulación ni build. La corrección de exportación se verifica en código fuente mediante prueba funcional de Desktop, no en rc9.

Capturas reales: `captures/01-rc9-start.png`, `02-new-dialog.png`, `03-save.png`, `04-new-filled.png`, `05-desktop-state.png`. La última demuestra el impedimento del entorno, no un defecto de Dino. El proceso rc9 se deja abierto en el diálogo de guardado; no se fuerza su cierre ni se guarda sobre proyectos existentes.

## Matriz funcional

Fuentes oficiales: [EngMod2T](https://vannik.co.za/EngMod2T.htm), [Post2T outputs](https://vannik.co.za/EngMod2T%20-%20Outputs.htm), [MOTA overview](https://www.iwt.com.au/mota-software/overview/), [MOTA samples](https://www.iwt.com.au/mota-software/samples/). Consulta 2026-10-29. El enlace al manual desde la página oficial de MOTA devuelve 404; no se atribuyen detalles no consultados. La documentación muestra capacidades anunciadas, no una prueba independiente de precisión.

Leyenda: U=implementada y usable; D=implementada con dificultad; C=núcleo sin acceso Desktop demostrado; A=ausente/necesaria; F=fuera del alcance. NV indica falta de nueva comprobación gráfica, no ausencia de función. Evidencia previa: `results/dino-trial-rc9-package-acceptance-20261029/receipt.json`; no sustituye este recorrido práctico.

| Capacidad | Referencia comercial documentada | Dino y evidencia | Clasificación |
|---|---|---|---|
| Crear motor monocilíndrico | MOTA: dimensiones por menús; EngMod: preprocesador Dat2T | Diálogo real, nombre sintético y motor creados; valores iniciales marcados supuestos | U, GUI parcial |
| Cilindro/cárter/unidades | MOTA exige geometría completa | Controles mm/cm³ y magnitudes derivadas visibles en rc9; modificación y límites no probados en GUI actual | D/NV |
| Distribución/puertos/transferencias | MOTA admite cambios de porting | Tabla rc9 muestra eventos derivados y roles técnicos en inglés; edición profunda NV | D/NV |
| Admisión/láminas | MOTA anuncia pistón, láminas y disco | Selector rc9 pistón/láminas visible; pruebas funcionales existentes de unión al solver; disco fuera del alcance implementado | U para selector, NV edición; F disco |
| Escape dimensional | MOTA cámara/silenciador; EngMod análisis de ondas | Página Escape y comparación existentes; no recorrida durante esta prueba | NV, sin nueva certificación |
| Guardar/reabrir/duplicar | Recorrido necesario del producto | Guardado alcanzó diálogo Windows; bloqueo impidió confirmar; duplicación no recorrida | NV |
| RPM, modelos y recursos | MOTA ejecución y comparación; EngMod simulador separado | Barra rc9 muestra 3000 rpm, 1 ciclo, 60 s; no ejecución nueva | NV |
| Progreso/cancelación/checkpoint | Documentación consultada no permite comparar detalle | Aceptación previa rc9; nueva interacción pendiente | NV |
| Potencia HP/kW/CV y torque | Post2T curvas por RPM; MOTA gráficos de prestaciones | Selector y panel existentes; sin nuevo uso gráfico ni curva calculada | NV |
| Superposición A/B/lectura RPM | Ambas herramientas comparan configuraciones | Evidencia previa y pruebas existentes; recorrido gráfico pendiente | NV |
| Presión/flujo/PV por ciclo | Post2T clasifica resultados por ángulo, RPM y desplazamiento | Vistas requieren primarios auditables; no comprobadas gráficamente ahora | NV; no declarar ausente |
| Llenado/barrido | Post2T anuncia delivery ratio | Transporte existe; acceso específico y significado físico no verificados; no añadir controles sin cierre identificado | C/NV |
| Mediciones | Post2T importa trazas y curvas de banco | Importación y contraste existentes; GUI actual pendiente | NV |
| Exportar/reutilizar histórico | Post2T datos numéricos reutilizables | CSV de Desktop antes no tenía JSON requerido por su propio importador; corregido y prueba funcional pasa | D → U automatizado, GUI pendiente |
| Reabrir CSV exploratorio | Reutilización necesaria, alcance de tabla frente a evidencia | Exportación tabular no contiene los primarios que exige auditoría; aviso explícito conserva artifacts originales | D; no se concede validación por CSV |
| Multicilindro/turbo/optimización automática | EngMod multicilindro/mapas; MOTA optimizadores | No requisito de esta entrega monocilíndrica | F |

## Escenarios de la prueba real

1. Crear: alcanzado; nuevo proyecto `synthetic-product-review`, motor `SYNTHETIC 125`.
2. Configurar geometría: controles visibles; no se certifica edición completa.
3. Escape: pendiente.
4. Guardar/cerrar/reabrir/duplicar: diálogo de guardado alcanzado; operación sin confirmar por bloqueo Windows.
5–9. Simulación, cancelación, recuperación, curvas, A/B y trazas: pendientes de uso gráfico en esta evaluación. Ninguna campaña iniciada.
10. Exportar/reutilizar: defecto reproducido por contrato importador/exportador y corregido con prueba funcional automatizada, sin presentarlo como prueba GUI.

## Defectos y fricciones priorizados

| ID | Prioridad | Evidencia y reproducción | Esperado/cambio mínimo | Estado |
|---|---|---|---|---|
| EXPORT-01 | P1 | Importar reporte histórico, exportar tabla CSV, abrir CSV exportado: faltaba JSON compañero requerido por `load_results` | Exportar CSV + JSON con identidades, unidades, clasificación, valores y hash del CSV; reabrir por ruta existente | Implementado; test funcional |
| EXPORT-02 | P1 | CSV histórico reabierto se trataba como importación externa genérica, mientras JSON se identifica histórico | Leer schema del compañero también para CSV y conservar aviso histórico/sintético | Implementado; test funcional |
| EXPORT-03 | P2 | Tabla exploratoria no es paquete de primarios y no sirve como archivo de recuperación | Explicar en tooltip y confirmación qué conservar para reabrir; no inventar evidencia desde CSV | Implementado |
| LABEL-01 | P2 | Captura 01: `intake`, `transfer`, `exhaust`, identificadores internos en tabla de lumbreras | Etiquetas en español con identificadores técnicos disponibles en detalles, tras probar edición | Pendiente |
| INPUT-01 | P2 | Captura 01: procedencias extensas y campos `sin clasificar`; formulario inicia en plantilla | Mejorar lectura por grupos sin sustituir datos desconocidos ni inferir geometría real | Pendiente; observar edición antes de modificar |
| ENV-01 | Bloqueo externo | Captura 05 y error real `no active desktop` | Desbloquear sesión Windows y continuar recorrido desde guardado | Pendiente |

No hay P0 de producto demostrado. No se confunden el bloqueo de Windows ni la falta de datos experimentales con defectos de la interfaz.

## Implementación y límites

Se reutiliza el schema histórico y el importador existentes. Se mantienen unidades, identidades y puntos inválidos como huecos; se verifica el hash al reabrir. El compañero existente se protege frente a sobrescritura. Se informa al usuario que ambos archivos son necesarios. No se cambia física, baseline, versión empaquetada ni selección experimental.

La nueva prueba usa datos sintéticos inválidos a propósito, exporta, reabre por el servicio y la página de Desktop, comprueba procedencia histórica, estados/unidades/identidades, protección del compañero y rechazo de CSV alterado. La aceptación gráfica y el caso real histórico del entorno siguen pendientes; el test histórico existente puede omitir por falta de raíz configurada.

Siguiente trabajo concreto: con Windows desbloqueado, completar guardar/reabrir/duplicar, editar escape e iniciar/cancelar un punto acotado; después cargar históricos compatibles, recorrer A/B/trazas y probar el CSV+JSON desde la interfaz de desarrollo. No se necesita un build para esa comprobación. Solo después corresponde decidir aceptación integrada.
