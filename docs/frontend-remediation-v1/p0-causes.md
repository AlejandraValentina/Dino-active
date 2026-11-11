# Re-evaluación estructural de los tres P0

Base examinada: producto d44305c y evidencia de auditoría 696b8fc. Esta evaluación
es una pasada técnica distinta sobre el código, no una INDEPENDENT_REVIEW por
otro agente. El criterio de cierre incluye ejecución real posterior.

## UX-001: el borrador no tenía una frontera de comandos

El editor guardaba texto en celdas, mientras guardar, ejecutar y cambiar variante
operaban sobre DesktopContext. `changed` significaba tanto cambio de motor como
publicación de resultados y reconstruía todas las celdas. La solución introduce
resolución explícita de borradores en los comandos, retorno de éxito al aplicar,
conservación ante notificaciones ajenas a la edición y bloqueo de edición durante
un punto/curva nativos. Una cancelación no debe enviar la configuración vieja.

Se mantiene separada la identidad de la configuración aplicada del documento
guardado; los archivos científicos no obtienen un campo de revisión inventado.
La siguiente fase presenta esas identidades en la cabecera común.

## UX-002: la exportación confundía referencia directa con cierre transitivo

Copiar summary.json y run.json cambiándoles de carpeta no conserva la semántica
de las rutas relativas del manifiesto primario. V2 del bundle conserva los bytes
y la disposición relativa de metadatos, manifiesto, configuración y traza. Las
referencias externas editables se rebajan a la raíz importada; las primarias no
se reescriben y sus hashes no se recalculan para ocultar cambios.

La importación prepara una carpeta nueva y valida antes de publicarla. La cadena
se reevalúa y los estados de integridad se muestran aparte del estado de
ejecución y la periodicidad. Los bundles V1 siguen siendo legibles, con su alcance
explícito. Los legacy permanecen no verificados; la resolución de compañeros
locales permite transportarlos sin afirmar autenticidad del origen.

Una exportación parcial conserva lo disponible y declara ausencias. Los estudios
2T con dependencias externas no cubiertas se señalan expresamente como parciales.
El formato V2 limita tamaño descomprimido y rechaza rutas de escape/ambiguas.

## UX-003: el tipo de ruta escapaba de la frontera de persistencia

El importador devolvía str y el contexto lo conservaba, pero Guardar esperaba
Path antes de entrar en su try. Se normaliza en el contexto y defensivamente en
Guardar dentro del manejo de fallos. Dirty sólo se limpia tras persistir y un
error mantiene el archivo y el trabajo en memoria. No se sobrescribe el proyecto
original al importar o recuperar.

## Evidencia inicial y de implementación

Las seis regresiones nuevas fallaron sobre la base sin corregir. Tras la
corrección, 30 pruebas de integridad/contexto/lifecycle/bundles pasaron, incluyendo
relectura del bundle con acceso al origen denegado, bytes originales iguales,
entrada inválida, cancelación de borrador, destino existente, rutas hostiles y
legacy no promovido. Los logs resumidos están en
`results/frontend-remediation-v1/verification/`.

Estado de esta fase al commit de implementación: IMPLEMENTED. SOURCE_ACCEPTED
requiere completar los recorridos reales y la regresión integrada. No se infiere
WINDOWS_ACCEPTED de una prueba de fuente en Windows. UAT humano queda separado.
