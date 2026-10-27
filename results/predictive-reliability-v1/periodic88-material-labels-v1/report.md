# Marcadores retenidos en39: desplazamiento central y cambio aguas arriba

2026-10-27. Diagnóstico de sólo lectura, cero pasos nuevos. Fuentes: nativos
38/39 y flujos SSPRK2 medidos por replay exacto39 (`7a6d70f`). Tests de
invariantes/traslación/reversión del diagnóstico:4 PASS. L1/SELF_REVIEW.

En un conducto sin fuentes de especies,
`a(x,t)=integral_izquierda^x rho A dx − integral_inicio^t mdot_izquierda dt`
es una etiqueta material del problema continuo. Las fracciones son constantes
en cada partícula de ese modelo sin mezcla molecular. Calor de pared cambia
el estado termodinámico, pero no transforma esos marcadores.

Las inversiones en ambos extremos requieren excluir material que pudiera
haber salido y reingresado. Usando flujos brutos de39, un intervalo seguro de
etiquetas originales es `[44.589730mg, 1802.536627mg]`: se excluye al menos
la descarga bruta hacia el cilindro por la izquierda y la salida bruta por la
derecha. Esto conserva88.2109% de la masa original. No se presupone que la
reversión de salida sea cero. Es una cota conservadora, no máxima retención.

Comparamos fracciones finales con el promedio exacto del perfil inicial
**constante por celda** sobre cada intervalo material final. También se
compara con la celda física inicial, usando exactamente los mismos índices
finales y pesos de masa en cada fila. No restamos normas ni usamos aquí los
umbrales de periodicidad. Sólo entran celdas completas dentro de la cota.

|Origen del material por centro inicial|Celdas finales|Quemados L1 material alineado|Quemados L1 sin alinear|
|---|---:|---:|---:|
|Todo el retenido evaluable|44|.0218283|.0018559|
|0–.2m|3|.1580367|.0005022|
|.2–.4m|5|.0630349|.0006665|
|.4–.8m|34|.0006244|.0022692|
|.8–1.079m|ninguna retención garantizada|no evaluado|no evaluado|

Los intervalos y cobertura efectiva de masa se registran en `analysis.json`.
El material identificado por su posición inicial termina en otras celdas:
las tres del primer grupo son17–19, no las primeras tres del escape. Los
grupos no cubren exactamente las mismas masas ni deben promediarse por número
de celdas. Las normas no son las L1 volumétricas de los informes anteriores.

## Interpretación proporcionada

En el material que comenzó en el tramo central, alinear por masa reduce la
discrepancia: existe contribución clara de desplazamiento/compresión. En el
material de origen próximo al cilindro, el cambio de marcador supera mucho
el cambio en las celdas físicas a fase fija. Un perfil casi repetible en
coordenadas fijas no demuestra que cada marcador se transporte sin alteración.

Esto señala transporte/mezcla numérica y representación subcelda como
incertidumbre adicional localizada. **No es todavía un error cuantificado
contra la solución exacta del motor**, ni prueba de un defecto de implementación:
el perfil inicial continuo no está resuelto por sus medias, y la trayectoria
de gas también tiene error discreto. El residual no debe llamarse mezcla
física ni atribuirse exclusivamente al limitador, HLLC o la frontera.

Antes de un nuevo ensayo, verificar cuánto depende esta conclusión de tomar
un perfil inicial constante frente a una reconstrucción lineal acotada con
las mismas medias de marcador. Esa prueba es algebraica, no requiere ciclos.
Si la señal persiste, diseñar un control breve de transporte bajo las ondas
existentes y refinamiento, preferiblemente antes de apertura del escape para
separar influencia de suministro desde cilindro. Conservar temporal/geometría/
remallado como incertidumbres distintas.

No ejecutar41 ni resolver la incertidumbre acumulando ciclos. No se modifica
ninguna formulación.88 sigue transitorio,44 periódico conserva su alcance;
rc7 intacta, sin independencia de malla ni validación predictiva experimental.
