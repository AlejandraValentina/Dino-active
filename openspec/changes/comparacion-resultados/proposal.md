## Why
Comparar dos geometrías ya calculadas, con procedencia y condiciones explícitas,
sin repetir simulaciones. Primer tramo autorizado de entrega 6; entrega 5 intacta.

## What Changes
- Vista compacta desde Simulación 2T para cargar A/base y B/modificada por el lector existente.
- Compatibilidad explícita, diferencias de entradas, tabla y superposición de muestras.
- Exportación resumen/curvas CSV a una carpeta nueva, sin sobrescrituras.

## Capabilities
### New Capabilities
- `comparacion-resultados`: comparación de resultados guardados y exportación CSV.
### Modified Capabilities
Ninguna consolidada. Núcleo, contratos de resultados y JSON v5 se conservan.

## Impact
Python estándar y Qt Widgets, sin nuevas dependencias. Sin solver nuevo, condiciones
editables, barridos, importación experimental, sesión persistida, archivo o entrega 7.
Entrega 6 En curso; publicación del commit propio a cargo de la usuaria.


## Ampliación autorizada posterior a b9fbee4d
La exclusión inicial de régimen/barrido queda limitada al tramo A/B ya registrado.
Este mismo cambio incorpora ahora punto entero 2500–3500 rpm y barrido secuencial
2–5 puntos, copia única/arranques independientes, resultados v3 e índice local,
tabla/puntos/CSV. Referencia fija, condiciones restantes y JSON v5 intactos.
Comprobación real limitada a B2500/3000/3500 y, si aprueban, C2500/C3500, sin
campañas extra. Importación experimental pendiente, entrega 6 En curso.


## Ampliación autorizada posterior a a72b47f4
Importación CSV por RPM y contraste descriptivo con barrido existente, sin calcular.
Magnitudes explícitas: trabajo indicado completo de un cilindro 2T o pmax absoluta
(Pa/bar). Procedencia declarada, copia original/metadatos, lectura validada, tabla,
puntos y CSV fiel. Implementar con pruebas sintéticas no equivale a contrastar
mediciones reales ni validar experimentalmente; esas comprobaciones siguen pendientes.
