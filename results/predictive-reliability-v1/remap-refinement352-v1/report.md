# Control adicional352: resultado y decisión

2026-10-27. SELF_REVIEW, L1. Único caso preregistrado en `5446ee1`:
352 celdas totales/248 escape, P0 desde el checkpoint25 original, una
revolución, paso máximo.0625°. Misma física, geometría, CFL y tolerancias.

**COMPLETO:335.97s<420s.** Sin ampliar presupuesto ni iniciar otros
refinamientos. Inventarios iniciales conservados hasta2.04e-15 relativo;
Euler restringido hasta1.27e-15. Restauración nativa final exacta.

## Comparación principal:176/.0625° contra352/.0625°

| Magnitud |176|352|
|---|---:|---:|
|Trabajo indicado J|131.198856|131.382184|
|IMEP bar|10.527217|10.541927|
|Salida bruta mg|213.474131|217.041718|
|Fracción quemada máxima final|.982635|.987168|
|Inventario quemados escape mg|1144.260465|1142.152806|
|Centro de masa de quemados m|.51021580|.51025144|

No hubo entrada por la salida. El trabajo cambia.1397%, la salida1.6712%,
y el inventario de quemados≈.1842%. Las diferencias locales de composición
siguen siendo importantes: pequeña variación integrada no implica igualdad.

En volúmenes físicos comunes44, la diferencia de presión L1 es.00422308 y
de quemados L1=.00573017. Los contrastes anteriores88→176 eran.00998366 y
.01266880: ahora **ambos se contraen**. Estos últimos tenían cap.125°;
el contraste temporal176.125/.0625 ya medido aporta sólo7.99e-5 y5.84e-6,
respectivamente, en esos mismos volúmenes.

No ajustar un orden asintótico/GCI: el trabajo sigue sin una secuencia global
monótona y su incremento176→352 es mayor que88→176. Este es un transitorio
común, no una solución periódica ni referencia exacta. La nueva contracción
de composición es evidencia favorable, no independencia certificada.

## Frentes, coordenada material y balances

Los tres cruces de quemados=.5 pasan de x=.066945/.237993/.299704m a
.061184/.243117/.296236m. La capa sigue desplazándose y afinándose. La
pendiente máxima crece19.24→34.55m⁻¹; no usar ese crecimiento como divergencia
por sí solo ni confundir variación total/pendiente máxima con anchura única.

El residual de medias de marcadores del material inicial retenido, comparado
en coordenada de masa con el perfil original, baja para quemados L1 de
.0037675 a.0026858. Los intervalos cubiertos completos son ligeramente
distintos y están publicados. El L∞ no tiene por qué caer monótonamente en un
frente; aquí crece.07434→.08504 mientras bajan L1 y L2. Se conserva también la
comparación por tramos en un intervalo común, sin exigir identidad puntual.

Máximo residual por especie/conducto2.42e-18kg, masa3.05e-19kg. Fuentes de
combustión y calor siguen incluidas en los balances globales de los receipts.
La comparación de presión media directa da L1=.00423948, frente a.00422308
desde medias conservadas; la diferencia de proyección no explica el efecto.

## Tiempo y reproducibilidad

176 empleó5762 pasos y352 empleó5790. Mediana y máximo.0625° en ambos;
352 rechazó28 propuestas por los controles existentes y aceptó60 pasos
menores al cap incluyendo eventos. No se afirma una secuencia temporal
idéntica ni que el contraste176 acote rigurosamente el error temporal352.
No se modificaron CFL, reintentos ni criterios de admisibilidad.

21 tests focalizados PASS, incluidos proyección hasta tercer refinamiento,
análisis sin ejecutar el solver y tratamiento explícito de resultados
incompletos. Configuración, primarias compactas, recetas, FAST intermedios,
checkpoint nativo, receipts y hashes preservados. Sin cambios de `motorsim/`,
sin push, sin alteraciones a rc7, históricos o controles resueltos.

## Dictamen

La evidencia es compatible con **capas físicas transportadas con difusión y
error espacial que disminuyen al refinar**, y con propagación de ondas también
sensible a la malla. No se ha demostrado un defecto de implementación. El
contraste inicial P0/P1 y temporal ensayados son insuficientes para explicar la
mayor parte de las diferencias espaciales. Geometría, propagación y frontera
no están completamente separadas; el efecto posterior de sus donantes acoplados
tampoco se debe etiquetar como difusión escalar pura.

Se cierran estos refinamientos. Es razonable preparar el tramo periódico44
máximo4 ciclos/90s del diseño costeado: permitirá separar relajación temporal
de incertidumbre espacial sin campaña multi-malla. Debe partir del checkpoint
original25 y su detector, no de estos transitorios refinados. Su ejecución
requiere un protocolo propio registrado; no se lanza por este informe.

Periodicidad **no demostrada**, independencia de malla **no demostrada**,
validación experimental **no realizada**, capacidad predictiva **no declarada**.
