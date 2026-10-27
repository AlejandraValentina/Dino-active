# Control temporal176 antes de atribuir diferencias a la malla

Enmienda previa a la ejecución adicional, 2026-10-27.

El caso176/P0/.125° terminó en108.73s y2882 pasos; la mediana y máximo son
.125°. El contraste44/88/176 mantiene así el mismo paso efectivo principal.
El caudal saliente180.97/203.46/213.48mg parece converger, pero el trabajo no
es monótono y la diferencia L1 de composición en volúmenes comunes44 no
disminuye88→176. No hay referencia temporal176 para descartar interacción.

Se agrega **un único caso176/P0/.0625°**, mismo origen25 y mismo horizonte.
Presupuesto240s,16MiB adicionales; total de cinco casos nuevos≤720s.
No se reduce precisión para cumplir el presupuesto. Ante STOPPED se conserva
el estado FAST y receta, y se declara insuficiente el contraste temporal sin
extender automáticamente. No es continuación de periodicidad ni producción.

Comparar .125/.0625 en176 a fases y volúmenes iguales; registrar variación de
trabajo, flujo bruto/reverso/neto, normas y frentes. Esta diferencia es una
sensibilidad, no una cota rigurosa del error temporal. Mantener todos los
resultados previos, incluidos los que no exhiben convergencia espacial.
