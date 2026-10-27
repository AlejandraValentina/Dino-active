# Sensibilidad del diagnóstico material a la representación subcelda

2026-10-27. Cero pasos de solver. L1/SELF_REVIEW. Mismos nativos38/39 y
flujos medidos39; sin cambiar su contenido ni ninguna formulación del motor.

Se reconstruye el marcador inicial en coordenada de masa mediante una función
lineal limitada, monótona/acotada, con un factor común a las cuatro fracciones
para conservar su suma. Medias de masa por celda idénticas; pendientes de
extremos cero al no conocer estados exteriores. Es una referencia diagnóstica,
no una modificación de MUSCL ni una recuperación de información desconocida.

Error máximo de preservación de medias y suma de fracciones registrado en
`analysis.json` (orden de redondeo). Valores de cara en[0,1]. Tests de promedios
exactos, positividad y cierre:3 PASS.

|Material por posición inicial|Quemados L1 con referencia P0|Con referencia P1|
|---|---:|---:|
|Todo el retenido evaluable|.0218283|.0221929|
|0–.2m|.1580367|.1563099|
|.2–.4m|.0630349|.0644852|
|.4–.8m|.0006244|.0006556|

Los cambios aguas arriba persisten frente a esta variación conservativa de
la referencia inicial. No se explican simplemente por haber escogido P0 en
la comparación material. La coincidencia P0/P1 no acota todas las posibles
estructuras subcelda ni transforma estos valores en error exacto de Euler.

El diagnóstico refuerza dos contribuciones distintas: desplazamiento del
material en el tramo central, y alteración numérica/representación bajo el
flujo pulsante en material de origen próximo al cilindro. No demuestra aún
que exista una implementación incorrecta ni cuánto afecta a trabajo/potencia.

## Siguiente contraste justificado

Diseñar un horizonte corto desde el nativo38 guardado, durante los primeros
60° de la trayectoria39 ya calculada, antes de abrir el escape. Verificar
el cierre geométrico antes de iniciar; así no se incorpora nuevo suministro
desde cilindro en ese intervalo, manteniendo sus ondas, geometría y salida
originales. Reutilizar fases/flujos originales30/60° como control temporal.

Comparar88/176/352 con condición física común y remallado validado, paso angular
común suficientemente pequeño, control temporal y contraste P0/P1 si resulta
necesario. Registrar masa, energía, especies, ondas y cambios en coordenada
material; no usar sólo el máximo local. Presupuesto total explícito y paradas
antes de ejecutar. No calcular41 ni ampliar una campaña periódica.

No es validación experimental ni independencia espacial demostrada. No se
justifica cambiar el solver con esta evidencia. rc7 y todo el historial intactos.
