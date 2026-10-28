# Etapa 2 — resolución espacial experimental de ondas

Prerregistro, 2026-10-28. Alcance único autorizado: segundo orden sobre E2A;
sin E2B, campañas periódicas ni modificación de los cierres físicos.

## Implementación reutilizada

`second_order.py` es el verificador aislado histórico con una especie pasiva;
no es la ruta del motor integrado. Copiarlo dentro del motor perdería el
contrato de cuatro componentes y duplicaría integración y contabilidad.
El motor ya posee una implementación seleccionable completa:
`MUSCL_PRIMITIVE_SPECIES_BOUNDARY_CANDIDATE_V2`, configuración V8.
Se activa explícitamente en cuatro configuraciones nuevas, conservando
íntegros los originales E2A y la selección predeterminada de primer orden.

El interior usa minmod generalizado theta=1,5 sobre primitivas y composición,
con gradientes en centroides físicos. Escalado de pendientes mantiene rho/p
positivas y composición en el simplex; no recorta los promedios conservados.
V2 reconstruye también extremos mediante pendientes unilaterales limitadas:
el acoplamiento de lumbrera V2 y OPEN_END_PLENUM_V2 reciben esas trazas,
incluida la composición donante según el signo del flujo. Conductos de menos
de tres celdas conservan primer orden. Se mantienen HLLC y SSPRK2.
No se requiere cambiar código físico para utilizar esta capacidad existente.

## Congelación y observación

`results/e2-spatial-waves-v1/preparation/manifest.json` identifica código e
inputs. Las únicas diferencias con E2A son el selector espacial y CONFIG_V8;
tests verifican igualdad exacta del estado físico inicial, inventarios y de
todos los demás campos. A/B, 9000 RPM, dos ciclos transitorios independientes,
44/88 celdas totales (31/62 escape), pasos nominales 0,5° y control fino 0,25°.
Se conservan CFL0,4, condiciones, geometrías y modelos E2A.

Mismas sondas físicas de 10 mm en 0,040/0,250/0,550/0,800/1,020 m,
ponderadas por volumen real de intersección con celdas. Se observa el campo
promedio por celda, sin introducir una interpolación de sensor diferente.
Mismos segundo ciclo, ventanas, amplitud, fase, impulso, correlación y
envolvente empírica de sensibilidad de E2A. Dicha envolvente no es una cota
rigurosa ni una incertidumbre estadística. Las hipótesis acústicas y su
rechazo se conservan: ningún pico se identifica automáticamente como reflexión.
No se extrapolan resultados a potencia periódica o validación experimental.

## Secuencia y presupuesto

1. Tests focalizados existentes V2: positividad, simplex, choques, contacto,
   conservación, fronteras, compatibilidad de configuración/reinicio y control
   histórico sin cambio del primer orden. Tests nuevos de congelación E2A.
2. Repetir referencias aisladas pequeñas de onda acústica suave y entropía
   con 40/80/160 celdas y CFL0,2, inyectando explícitamente reconstrucción V2
   en el verificador; incluir pulso gaussiano acústico 1e-6 frente a solución
   linealizada, declarando error no lineal O(amplitud²). Error L1 y orden,
   amplitud, posición y conservación. No exigir orden dos en discontinuidades.
3. Sólo si pasan: seis ejecuciones nuevas E2A, 44/88, controles temporales
   idénticos. Reutilizar primer orden publicado, sin recalcularlo.

Máximo acumulado **600 s**, incluida verificación y, conservadoramente,
análisis. Reservar 20 s para cierre. Máximo 120 s por caso; 512 MiB RSS,
1 GiB de artefactos y preflight con margen antes de escribir. Parada segura
sin ampliación. Checkpoints nativos por revolución; dentro de una revolución
conservar terminal FAST y receta junto al último checkpoint nativo, sin
presentar ese terminal aislado como checkpoint reanudable.

El paso nominal 0,25° no garantiza dividir todos los pasos reales: registrar
los dt aceptados y no declarar independencia temporal absoluta.

## Decisión congelada antes de ejecutar

- Control aislado: órdenes finales ya establecidos >=1,7 en entropía/especies,
  >=1,6 en acústica y conservación absoluta <=1e-11. Pulso: orden >=1,6,
  reducción de error L1 >=2 en 80 celdas, conservación <1e-11.
- Integrado: residuo relativo masa/especies <=1e-9, energía <=1e-8,
  restauración exacta de checkpoint y admisibilidad del solver sin relajar.
- Mejora material: reducir >=30% la suma de sensibilidades espaciales de
  amplitud A y B respecto a E2A; coste del solver <=3 veces las mismas seis
  ejecuciones originales (incluido A44 reutilizado, con su coste original).
- **ADOPTAR COMO CANDIDATO**: controles, mejora y coste cumplen, y amplitud y
  fase A/B distinguibles con el criterio E2A inalterado.
- **MANTENER EXPERIMENTAL**: evidencia favorable pero A/B aún no resuelto,
  mejora material no demostrada o presupuesto insuficiente. No promoción.
- **DESCARTAR**: inestabilidad, fallo conservativo o coste >3 veces.

No se cambian límites después de ver resultados. Revisión SELF_REVIEW;
ningún claim externo de precisión o sustitución de rc7. Entrega y parada.
