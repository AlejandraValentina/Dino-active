# Dictamen de convergencia de frentes, 2026-10-27

**Transporte aislado: comportamiento numérico esperado en los casos ensayados.
Motor integrado: incertidumbre espacial todavía no resuelta.** No se encontró
un defecto que justifique cambiar MUSCL, acoplamiento transónico o salida.
SELF_REVIEW; sin validación experimental ni afirmación de precisión predictiva.

Se ejecutaron17casos de referencia y4con la salida real OpenEndPlenumV2, sobre
32/64/128celdas, incluyendo paso temporal mitad. Tiempo77.72s y28.80s,
respectivamente; no son benchmarks de velocidad del producto. Cuatro pruebas
analíticas verifican integrales exactos, envoltura periódica, normas y cruces.
El presupuesto por invocación fue120s y8MiB/4MiB. Perfiles finales, recetas
matemáticas y fuentes están preservados; estos son fixtures L1, no checkpoints
nativos del motor. Ninguna física/código productivo fue modificada.

## Frente de especie, MUSCL V2, contacto compresible con salida

| Celdas | L1 fracción | L2 | Linfinito | Posición50% (exacta.85m) | Anchura10–90% |
|---|---:|---:|---:|---:|---:|
|32|.029051|.076701|.317522|.848181|.112450m|
|64|.015035|.054030|.303316|.849613|.066824m|
|128|.010226|.048274|.358908|.850008|.039671m|

L1/L2 y anchura decrecen; amplitud máxima.985896/.999861/.99999999 sin
sobreoscilación. Linfinito no es monótono. Una capa de error de amplitud O(1)
y anchura que disminuye puede tener L1 que tiende a cero mientras conserva un
máximo O(1). Su valor también depende de qué fracción de celda ocupa el salto.
Por eso no se exige convergencia puntual ni orden2 en una discontinuidad.
Tres mallas muestran mejora; no bastan para certificar régimen asintótico.
Las normas se calculan en coordenadas comunes contra promedios exactos. El JSON
incluye también comparación entre mallas después de restricción conservativa.
Se conserva error de densidad de especie además de fracción másica, pues en un
contacto su promedio de volumen no coincide con su promedio ponderado por masa.

## Separación de mecanismos

- Periódico sin frontera física: L1 de fracción.056989/.030563/.021370, con dos
  frentes; anchura del frente ascendente.11438/.06700/.04025m. La difusión y
  Linfinito no monótono existen sin salida ni geometría variable.
- Salida con transporte pasivo: MUSCL V2 L1.029514/.015328/.010685; primer orden
  .079850/.054113/.040471. MUSCL conserva mejor amplitud y estrecha la capa.
  V1 frente aV2 difiere ligeramente cerca del extremo en malla gruesa y converge
  a resultados casi iguales; no explica por sí solo el error del frente interior.
- Contacto rho1/1.2,p=u=1: el mismo mecanismo converge con gas compresible.
  Presión permanece uniforme dentro de1.36e-14. Esta prueba tiene salto de
  densidad/entropía, pero no ondas acústicas, choques ni inversión del flujo.
- La frontera exacta usada por el caso motor, OpenEndPlenumV2.resolve+eos.flux,
  produce perfiles idénticos a Boundary(reservoir) en estos contactos salientes
  a presión ambiente. Esto verifica ese régimen, no la equivalencia general
  de ambas formulaciones. El control no reproduce el escape pulsante completo.
- Mitad de paso a128celdas: diferencia L1 de densidad de especie1.32e-5 pasivo,
  1.73e-5contacto, mucho menor que error espacial. No se cambió CFL del producto.
  Se controló a128; no se certifica separación temporal completa en cada malla.

## Conservación, caudal e interpretación física

Se usan los mismos flujos de cara en Euler/especies y libro de flujo integrado
promediado en ambas etapas SSPRK2. Residuo máximo de masa/momento/energía/especies
1.02e-14 en todos los casos. La especie0 saliente exacta del contacto es.12
unidades de masa; errores relativos1.163%/.04889%/.0001816%. El caudal acumulado
puede converger mucho mejor que el máximo local. No se alinea artificialmente
el frente para calcular normas: posición, amplitud y anchura son métricas aparte.

El conducto tiene volumen fijo y no calcula trabajo indicado o IMEP del motor.
En los resultados integrados existentes, el trabajo del segundo ciclo se calcula
por diferencia de ledgers360/720grados:59.8785/60.7844J. Usando la cilindrada de
slider_crank de esa misma configuración,124.628237cm3, IMEP bruta del ciclo2 es
4.80457/4.87726bar, diferencia1.513%. No confundir con3.30% de trabajo acumulado
sobre los dos ciclos, ni con potencia/IMEP periódica. Contexto JSON preservado.

## Decisión y próximo límite

No corregir el solver sobre esta evidencia. El transporte conservativo limitado
converge en normas integrales y métricas de frente; la malla gruesa difunde y
retrasa/desplaza frentes. Falta verificar conjuntamente presión pulsante, reversión
y reacción de salida en el rango del escape integrado. Es legítimo un piloto
acotado de estabilidad/periodicidad con checkpoints, pero no una campaña periódica
extensa ni una declaración de independencia de malla. Primero preparar un control
compresible pulsante de salida con balances de onda/especies y presupuesto120s;
si no identifica defecto, aplicar el protocolo de tercer nivel176celdas y luego
piloto máximo10ciclos/240s previamente registrado, sin extensión automática.
La comparación predictiva continúa bloqueada por datos y error espacial del motor.
