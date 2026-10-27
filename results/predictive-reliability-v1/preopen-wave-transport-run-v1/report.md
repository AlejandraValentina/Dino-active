# Ondas antes de apertura: contracción medida, alcance limitado

2026-10-27. Preregistro/runner `ba901ff`, preparación `4067344`.
COMPLETE en198.056s<480s. Cinco casos admitidos según coste y regla P1.
L1/SELF_REVIEW. Sólo0–60° de la trayectoria39 desde nativo38; ningún41 ni
ciclo periódico nuevo. Solver, modelo físico, tolerancias y rc7 intactos.
Caso sintético de verificación a9000rpm; no es una reconstrucción del X30.

## Controles y resultados

En todos los stages, transporte cilindro→escape cero, conservando reflexión
en esa frontera cerrada y salida original. Sin inversión exterior en este
arco; la inversión medida durante el ciclo completo ocurre después. Balances
globales/por celda pasan: máximo normalizado2.38e-13<1e-12. Ningún rechazo.
Las tres mallas usan960 pasos de.0625°; temporal176 usa1920 de.03125°.

|Caso|Segundos|Masa saliente bruta mg|Quemados L1 material en intervalos comunes|
|---|---:|---:|---:|
|P0-88|19.518|30.335269|.00235234|
|P0-176|31.237|31.285229|.00129548|
|P0-352|53.928|31.614960|.00104603|
|P0-176 paso mitad|61.779|31.285241|.00129546|
|P1-176|31.457|31.340617|.00069392|

Los intervalos materiales retienen98.4136% de la masa inicial, con pesos de
masa fijos del estado88. Son cambios respecto al marcador inicial representado,
no error exacto de Euler. P1 es otra hipótesis subcelda con iguales medias,
no una mejora física demostrada. Trabajo del arco150.522595J idéntico entre
mallas/P0/P1 a cap común; dt2 da150.524173J. No es trabajo de ciclo ni IMEP.

Campos a60° sobre volúmenes físicos comunes88; fracciones absolutas y
presión/densidad relativas. Iniciales P0 equivalentes hasta redondeo.

|Métrica|88/176|176/352|176 dt/dt2|
|---|---:|---:|---:|
|Presión L1|.0028712|.0012826|.0000062114|
|Densidad L1|.0025980|.0010358|.0000046106|
|Quemados L1|.00092215|.00033375|.00000017936|
|Quemados L2|.0023950|.00080257|.00000056354|
|Quemados L∞|.0120822|.0036609|.0000032373|
|Diferencia relativa masa saliente|3.03645%|1.04296%|.00003847%|

Hay contracción espacial de ondas, marcadores y caudal integral, con señal
temporal mucho menor. Original88(.25°) frente a.0625°: presión L1 .00005978,
quemados.000003114, también menores. No Richardson/GCI ni orden asintótico.

La diferencia máxima de presión está en x=1.0165m sobre la malla común:
5.5054%→2.8945%. El mínimo promediado pasa.80272bar(x=.99864m)→.76786bar
→.74563bar(ambas x=1.0165m). La depresión próxima a salida cambia profundidad
y posición; el caudal no es sólo un problema de composición. La contracción
integrada no elimina esta incertidumbre local ni demuestra un defecto de frontera.

P0/P1 en176 cambia masa saliente.17673%, presión L1 .0002700 y quemados L1
.00074598. La representación inicial importa en composición; no explica por
sí sola el caudal espacial. No seleccionar P1 como verdad o calibración.

La presión derivada de q filtrado incluye varianza cinética subcelda. El
promedio volumétrico directo da L1 espacial.00287098/.00128243; el sesgo
medio del filtrado es≤2.65e-6, insuficiente para explicar la señal. Un test
analítico verifica esta distinción. Los marcadores no cambian γ/R y tienen
reconstrucción independiente del gas. Un probe algebraico inicial sustituye
marcadores del escape manteniendo q: RHS gas idéntico, transporte de especies
distinto, snapshot intacto. Tras apertura sí puede existir retroacción indirecta
por llenado/combustión; aquí no se atribuye el caudal a la fracción quemada.

## Normas materiales apropiadas y límites

En iniciales P0 equivalentes, la comparación puntual de perfiles discontinuos
da L1≈5e-17 pero L∞ .14–.16 en intervalos microscópicos por redondeo de
bordes. No es una diferencia física de esa magnitud. Se añadieron promedios
exactos sobre los mismos intervalos originales88, sin mover bordes, descartar
masa ni relajar tolerancias: máximo inicial P0=3.33e-16. El contraste final
88/176→176/352 contrae L1 .00140695→.00033982, L2 .00351512→.00083400,
L∞ .0140131→.0046067; temporal L1=5.10e-8.

Con las propias celdas finales y su diferente cobertura, el residual contra
el marcador inicial es no monótono:.001395→.002711→.002641. Todas esas
normas originales permanecen en JSON. La contracción demostrada es de campos
comunes/integrales, no convergencia fuerte de cada discontinuidad/subcelda.

## Localización posterior sin otra simulación

Las13 fases y flujos del39 existente permiten seguir intervalos materiales
fijos durante todo el ciclo (retención88.21%, distinta del98.41% anterior).

|Fase|Quemados L1 material, intervalos fijos|
|---|---:|
|60°|.0025735|
|90°|.0027459|
|120°|.0069650|
|150°|.0161300|
|210°|.0217720|
|360°|.0243595|

El crecimiento mayor aparece después de apertura, especialmente90–150°,
con suministro y ondas cambiantes. No identifica por sí solo un defecto del
acoplamiento: transporte interno/frentes/subcelda también participan.

## Dictamen y continuación

Transporte numérico compatible con convergencia de observables comunes en
0–60°, sin defecto demostrado. Temporal pequeño; espacio domina flujo;
representación inicial relevante para composición. Intercambio tras apertura
todavía incierto. No modificar MUSCL, HLLC, V2 ni salida; no ampliar campaña
periódica.88 sigue transitorio en40, sin independencia de malla demostrada.

Siguiente tarea: diseñar el contraste acotado del tramo90–150° de la
trayectoria39 existente, reutilizando recetas/estados con recuperación exacta,
control temporal y presupuesto. No se ejecuta automáticamente desde el informe.

Vista consolidada: `analysis-complete-v3.json`; versiones anteriores/fuentes
exactas conservadas. `input-manifest.json` sella casos; `run/` guarda iniciales,
recetas, FAST parciales, fases y balances. Figura revisada con barras desde
cero: `diagnostic-zero-baseline.png`. Sin validación ni claim predictivo.

Regresión focal:72 PASS en15.42s, resultado persistido en `regression/`.
