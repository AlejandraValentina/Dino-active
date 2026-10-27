# Frente88: relajación transportada, no defecto de contabilidad detectado

2026-10-27. Protocolo `9ad1a87`; L1, SELF_REVIEW. Sin nuevos ciclos:
replay únicamente38→39, configuración, reloj, combustión, CFL, tolerancias y
modelo intactos. No se calculó40. Fuente sellada en manifest de ventana2.

## Localización con estados existentes

Comparaciones de ciclos consecutivos, misma malla88, coordenadas y fase TDC.
L1/L2 de ΔY quemados ponderadas por volumen; L∞ local. Centro/anchura son
momentos de |ΔY|, **no** posición y anchura absolutas de un único frente:
hay varias estructuras espaciales, y sus pesos cambian.

|Relativo|x máximo m|Centro de discrepancia m|Anchura σ m|L1|L2|L∞|Δ quemados mg|
|---|---:|---:|---:|---:|---:|---:|---:|
|6|.50548|.48879|.11169|.0017355|.0024578|.0053894|−.78540|
|7|.53797|.51957|.09442|.0016583|.0023493|.0050608|−.97242|
|8|.57525|.55597|.09288|.0016799|.0023459|.0047641|−1.00876|
|9|.63234|.58930|.10989|.0017604|.0023802|.0046868|−1.00383|

La amplitud máxima baja mientras la estructura se desplaza aguas abajo y
L1/L2 repuntan ligeramente. Esto explica por qué el número fallido sube19→27
sin demostrar divergencia. Los27 fallidos finales son16 fracciones (aire/
quemados, celdas33–40) y11 masas (34–44); región x≈.575–.769m. No fallan
trabajo, energía de celdas, presión, cámaras ni inventarios globales en39.
Esto significa cumplimiento de esos umbrales, no identidad de esos estados.

En el relativo9,99.81% del peso |ΔY quemados| está en celdas con |Δp|/p<.001.
Presión L1 relativa cae .000729→.000299 entre6–9. La descomposición local
linealizada δρ=δp/a²+resto da términos L1 de **.453mg y2.611mg** respectivamente
en9, expresados como integrales de densidad. Las
unidades de los datos son kg (4.532e-7 y2.611e-6kg); no son un balance de
masas independientes. El resto domina y es compatible con un modo de
composición/densidad/temperatura a presión casi repetible. No constituye una
descomposición no lineal exacta ni demuestra ausencia de error espacial.

Lag2 máximo4.938→4.388 sigue peor que lag1; no hay período2 admitido.
Trabajo39=135.923446J, IMEP≈10.906bar; cambio propio38→39=.06453%.
Respecto al44 periódico130.923315J, diferencia≈3.82%, sin atribuirla a una
solución periódica88 todavía inexistente. Aire a300°=104.0688mg, calor
químico/ciclo258.3329J: no hubo calibración ni incremento artificial.

## Replay y flujos efectivamente medidos

1440 pasos aceptados y718 propuestas rechazadas reproducidos. Checkpoint
nativo final, estado, ledger, eventos y reloj **exactos**.49.719s<120s;
watchdog150s. Flujos SSPRK2 de ambos stages con sus signos reales, ya
integrados en área. El terminal se compara también después de compactar la
receta: no se limita a comparar potencia.

|Interfaz|Flujo positivo mg|Flujo negativo mg|Neto mg|
|---|---:|---:|---:|
|Cilindro→escape|235.922717|−44.589730|191.332986|
|Escape→exterior|190.353686|−.799465|189.554222|

Reversión cilindro en210–270°, y salida en210–240° según ventanas30°.
Las ventanas no fijan exactamente el instante del cambio de signo. La
reversión del cilindro es18.90% del flujo positivo; la exterior.420%.
No puede suponerse ausencia de reversión extrapolando diagnósticos anteriores.

Balance del escape durante39:

|Cantidad|Inventario Δ|Transporte neto|Fuente|
|---|---:|---:|---:|
|Masa mg|+1.778764|+1.778764|0|
|Aire fresco mg|+2.577372|+2.577372|0|
|Combustible mg|+.205220|+.205220|0|
|Residuales mg|−.000000572|−.000000572|0|
|Quemados mg|−1.003827|−1.003827|0|
|Energía J|+.228745|+6.793728|−6.564983 a pared|

Quemados entran netos111.047193mg y salen112.051020mg. No hay reacción en
escape; su disminución coincide con transporte. La masa total inicial
1992.890313mg pasa a1994.669078mg. La suma de |Δ masa quemados por celda|
baja de2.1706 a2.0586mg entre6–9, aunque L1 de fracción repunta: inventario,
concentración y error local no son la misma métrica.

Balances por cilindro, cárter, admisión, tres transfers y escape incluyen las
fuentes químicas/P7, −p dV y calor de pared observados. Máximo residual
normalizado3.305e-14<1e-12; residuo de masa del escape8.67e-19kg. El calor
transportado usa flujo de energía total/entalpía; inventarios usan energía
total en conductos e interna en cámaras. Sin doble multiplicación por área.

Inventario medio/caudal bruto exterior=10.474 ciclos=.06983s a9000rpm. Es un
diagnóstico de renovación, **no** tiempo de convergencia, constante exponencial
ni presupuesto de ciclos restantes: hay distribución espacial y recirculación.

## Dictamen y próximo paso

**Relajación transitoria del sistema discretizado todavía activa**, con
estructura de composición/densidad que se desplaza; no hay defecto demostrado
de implementación dentro de los controles realizados. El repunte de L1 y
conteo no equivale a un inventario divergente sin explicación. Las diferencias
de inventario están explicadas por transporte y calor medidos.

No se separa por completo el transitorio físico de la difusión/dispersión
numérica: la malla88 cambió la evolución y aún no tiene un período aceptado.
No procede modificar MUSCL, HLLC, V2 ni salida. Se justifica **preparar** una
siguiente ventana corta desde39, con detector intacto y criterios de detención
que sigan amplitud, desplazamiento, inventarios y presión/trabajo. No hay
autorización implícita para extender hasta PASS. Sólo después de periodicidad
88 y control temporal corresponde comparar mallas periódicas y evaluar176.

Sin independencia de malla, validación experimental ni capacidad predictiva
declaradas. rc7 y evidencias históricas intactas. Datos completos en
`run/saved-fronts.json` (13 fases/ciclo) y `run/receipt.json` (flujos, ventanas y
balances dimensionales/normalizados).
