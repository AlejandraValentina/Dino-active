# B. CONFIGURACIÓN BLOQUEADA

## Lo que sí queda reconstruido públicamente

Se incorporó el [manual IAME MAN-089](https://www.kartcompany.ch/images/iame/manual/E/MAN-089-ENG-X30-125cc-Spec-EU.pdf), revisión impresa MAN2018-89, PDF creado2018-06-01. Su tabla final (PDFp19/página impresa18) publica cámara nominal10,15cm³, escape177,5°±2° y avance fijo22°. El ajuste430–440mm (PDFp7) va desde la brida del colector a la primera soldadura del primer cono, no hasta la salida completa. El [artículo2023](https://www.mdpi.com/1996-1073/16/13/4947), sección3.1, documenta lambda0,85 y22° para su simulación; no los transforma en mediciones del ejemplar del banco.

La homologación254/V (12/11/2020, archivo REV.05/AGG2021) permite una reducción nominal: cinemática54×54mm y biela102mm; referencias de distribución y anchos cordales; secciones y cotas de admisión/láminas; planos acotados de escape y montaje. Se revisaron además sus páginas3,44–46 de cigüeñal y útiles de control. No se mezclan revisiones como si fueran una medición del mismo motor. MAN-089 publica177,5°±2°, mientras254/V limita a177,5° máximo: se conserva esa diferencia, no se importa toda la tolerancia antigua al contrato posterior. Tampoco se identifica L del manual con una cota M/N/T del plano sólo por parecerse numéricamente.

|Referencia nominal|Apertura ATDC|Cierre ATDC|Desplazamiento de pistón desde PMS|
|---|---:|---:|---:|
|Escape177,5°|91,25°|268,75°|31,226mm|
|Transfers126°|117,00°|243,00°|42,135mm|
|Transfer127°|116,50°|243,50°|41,951mm|

Son derivaciones bajo control simétrico de pistón y duración nominal, no un mapa medido de área. La galga0,2mm, chaflanes y radios deben distinguirse de apertura de área cero. Los anchos cordales pueden convertirse en límites de arco; las alturas descubiertas hasta PMI son cotas superiores, no alturas completas de ventanas. La sección proyectada permite una aproximación1D declarada de transfers; no revela sus secciones fuera del plano. Un perfil reducido, un ajuste nominal dentro del rango de escape y cierres térmicos/combustión explícitos son hipótesis preliminares posibles, sin ajuste a potencia.

El inventarioV2 añade estos avances y mantiene los anteriores como historial. La cámara10,15 ya no se trata como un valor nominal ausente. La relación con el inserto de comprobación2cm³ mostrado en254/Vp5 sigue requiriendo una convención explícita: no se resta2cm³ automáticamente ni se presenta una relación de compresión condicional como medida.

## Dato esencial que sigue faltando

**Volumen libre del cárter de precompresión ensamblado en un ángulo definido —o relación de compresión primaria del X30 con la misma definición de volúmenes.**

Bajo la ley geométrica actual, r_primaria=(V_min+Vd)/V_min. Vd=123,671936cm³ es conocido; falta V_min. Las vistas públicas dan cotas locales y proyecciones, pero no el volumen3D de cavidades conectadas menos cigüeñal, biela y pistón. Una vista de cárter con una cotaØ64 y un ancho parcial de cigüeñal48,8mm no define una cavidad cilíndrica de precompresión: multiplicarlos produciría una geometría inventada. Los útiles de control44–46 tampoco cierran ese volumen. Los40ml de aceite de engranajes del manual pertenecen a otra función y no son volumen de gas de precompresión.

Este grado de libertad cambia la presión que impulsa los transfers y la masa fresca admitida. No hay un valor central ni un intervalo nominal X30 defendible en estas fuentes que permita fijarlo sin inventarlo. Se descarta copiar1,35 de otro motor. La falta del dato experimental privado por sí sola no es el motivo de bloqueo; el dato geométrico esencial sigue indeterminado incluso para el nominal.

## Cierre y solicitud mínima

No se crea una configuración ejecutable. [InventarioV2](x30-technical-inputs-v2.json) conserva documentados, derivados e incógnitas y ejecución deshabilitada. Para desbloquear basta obtener ese volumen/relación con ángulo y fronteras: especificar si incluye conductos de admisión o transferencias, para no contarlos dos veces al representarlos aparte. Puede venir del fabricante o medirse volumétricamente en un X30 ensamblado con las fronteras de conductos definidas; no se exige CAD confidencial. Las longitudes/secciones representativas de transfers y la convención de cámara son aclaraciones adicionales útiles.

Se afinó el [correo ya preparado](email-draft-refined.md) con esa solicitud concreta, manteniendo la petición de datos originales del artículo. **No enviado.** No se investigaron otros motores, no se ajustó contra15,1kW, no se modificó el solver ni se ejecutaron simulaciones. Los datos públicos de la curva siguen siendo útiles para una comparación orientativa una vez cerrada esa geometría; no identifican el volumen faltante ni validan una reproducción experimental.

**Decisión definitiva de este trabajo: B. CONFIGURACIÓN BLOQUEADA por volumen de precompresión no determinado.** No se abre otra búsqueda ni se produce un X30 sintético para aparentar que ese dato está resuelto.
