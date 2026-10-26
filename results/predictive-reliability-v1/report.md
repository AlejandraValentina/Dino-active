# Confiabilidad predictiva V1: avance y hallazgo previo a adopción

## Estado

**Avance parcial. Restricción de referencia verificada; adopción de la nueva
conexión detenida por dominio transónico incompleto.** No se modificaron el motor
integrado, HLLC histórico, SSPRK2, geometrías, combustión, Desktop ni resultados
históricos. La baseline rc7 está preservada y su ZIP fue verificado nuevamente.

Esta intervención aplica la autorización de avanzar por dependencias físicas.
El dueño también pidió detener la parte afectada y presentar evidencia si surge
un problema fundamental que cambie la estrategia. El hallazgo siguiente activa
esa condición antes de integrar el candidato o modificar la reconstrucción.
No representa un HARD_STOP de almacenamiento, una pausa de todo el programa ni
una invalidación de los resultados históricos bajo sus modelos originales.

## Implementación y verificación

1. Contrato y orden de trabajo registrados antes del código: `10bb81a`, `69888c2`.
   La especificación fija pruebas físicas y no prescribe aumentar potencia.
2. `motorsim/port_restriction_v1.py`: restricción reversible entre volúmenes 0D
   en reposo, con Cd direccional, área geométrica explícita, límite sónico,
   entalpía total y especies del donante. Usa fórmulas estables cerca del equilibrio.
   **1029 pruebas** pasaron contra una referencia termodinámica Decimal de 80
   dígitos, incluyendo dimensiones, escalas, Cd, inversión y ausencia de deadband.
   Commit `7b6fe35`. No es por sí sola una frontera de conducto.
3. Contrato de conexión completa fijado en `2bc0a04`. El candidato
   `motorsim/port_connection_v1.py` distingue cámara, garganta y sección del tubo;
   combina curvas acústicas de choque/expansión con masa, energía y un cierre de
   expansión. Ofrece flujo de momento sobre la cara completa, evitando sumar
   dos veces la presión de área bloqueada. Permanece sin importar ni habilitar
   desde el solver o Desktop.
4. Los estados fabricados verifican el límite isentrópico de sección completa
   (incluido Mach bajo, donde la ruta histórica entrega aproximadamente la mitad
   del flujo), restricciones parciales, inversión de orientación y conservación.
   Los tests de excepción comprueban rechazo explícito; no convierten un caso no
   resuelto en una aprobación científica de dominio.

## Hallazgo fundamental del candidato

El barrido algebraico pequeño de 1008 estados, sin simulaciones de motor, obtuvo:

| Resultado | Valor |
|---|---:|
| Estados con solución en el dominio del candidato | 971 |
| Estados no resueltos, todos con interior subsónico válido | 37 |
| Máximo residuo relativo garganta–conducto de masa, resueltos | 1,02e-13 |
| Máximo residuo relativo de entalpía total, resueltos | 4,44e-16 |

Los 37 casos requieren un régimen de cara transónico/supersónico que esta
formulación candidata no contiene. No se rechazaron por CFL, inventarios negativos
o falta de precisión de la bisección. La cobertura completa del acoplamiento NO
ha pasado. `connection-domain-receipt.json` registra cada estado rechazado.

**Caso mínimo reproducible:** gamma=1,35; cámara 500 kPa y 300 K; interior de tubo
100 kPa y 300 K; Mach normal saliente -0,8 (entrada al tubo); área del tubo
1e-4 m2; área efectiva de garganta 5e-5 m2.

- Garganta sónica alimentada desde la cámara: requiere **0,0576073893 kg/s**.
- Máxima masa compatible con la rama subsónica de cara, energía y curva acústica
  del candidato: **0,0505520173 kg/s**.
- La demanda supera esa capacidad **13,9567 %**. El límite se obtiene invirtiendo
  analíticamente la curva de compresión, no del mismo buscador de raíces.
- Retirar sólo la condición subsónica conduce a Mach de cara **1,06104** en las
  ecuaciones restantes. Ese valor es un diagnóstico de rama faltante, no una
  solución adoptada ni verificada para el modelo completo del puerto.

Imponer el caudal de garganta y conservar arbitrariamente la velocidad o presión
de celda no satisface estas restricciones. Reducir el caudal para sostener la rama
subsónica tampoco sería una corrección justificada. Al cambiar el sentido de las
características hay que formular el nuevo régimen y sus condiciones de choque/
expansión; no se debe extrapolar la condición acústica saliente a todos los casos.

Esto cambia la estrategia de sustitución: **la implementación no puede limitarse
a una conexión característica siempre subsónica con una fórmula de garganta**.
Hay que verificar también la selección de régimen y su continuidad antes de
adoptarla en un motor. El fallo pertenece a la cobertura del candidato nuevo;
no demuestra que los 37 estados estén presentes en A9000 ni cuantifica un error
de potencia de Dino. Aún no se ejecutó una simulación con el modelo nuevo.

## Referencias preservadas y siguiente dependencia

`baseline.json` confirma el ZIP CRV1 rc7 contra SHA-256
`2bd3419d4fc710d751515ccccbbe098c61609d16aae68c1492e353dccc83755a`.
Referencia de desarrollo anterior: `e3be7e2`. P0-P9 no se modificaron.
El preflight pasó con estimación 0,1 GiB y reserva de 2 GiB; no hubo limpieza.

La integración, mejora espacial, diagnósticos de motor e identificación de cierres
siguen pendientes en ese orden. La dependencia inmediata es una conexión con
selección transónica y referencia independiente de sus choques/expansiones, además
de examinar el dominio real de los estados históricos. No se reabre V3 ni X30.
El defecto térmico de volumen móvil permanece registrado para su etapa; no se
habilitará esa combinación antes de corregirla y verificarla.

Reproducir la evidencia:

```text
python -m pytest tests/test_port_restriction_v1.py tests/test_port_connection_v1.py -q -p no:cacheprovider
python scripts/diagnostics/verify_port_connection_v1.py --output results/predictive-reliability-v1/connection-domain-receipt.json
```

Nivel: verificación matemática y numérica propia, **SELF_REVIEW**; validación
experimental y comparación predictiva con EngMod2T **NOT_PERFORMED**. Fuentes y
supuestos constan en las especificaciones previas a la implementación. Los
resultados de regresión se registran en `verification.json` y su log durable.

## Verificación final de esta intervención

- Suite focalizada: **1187 PASS**, 2,37 s; 1029 casos de restricción, 122 de
  conexión candidata y 36 regresiones existentes de acoplamiento/contorno/especies.
- Regresión P4-P8: primer intento **298 PASS, 3 SKIP, 3 FAIL**, 102,05 s. Los
  fallos se debieron exclusivamente a `DINO_ARTIFACT_ROOT` ausente. Los artefactos
  registrados existían y sus hashes se verificaron al resolverlos con la raíz
  correcta. Se repitieron sólo esos tres casos: **3 PASS**, 84,68 s.
- Resultado conjunto: **301 pruebas históricas ejecutadas PASS, 3 SKIP**, sin
  fallos sin resolver. Los skips pertenecen a comprobaciones históricas que
  dependen de archivos auxiliares generados; no se cambiaron para esta entrega.
- La comprobación de la cola pasó. Los cambios locales ajenos y la auditoría
  original untracked se conservaron sin stage. No hubo push.

El éxito de estos tests no cambia `ADOPTION_BLOCKED_DOMAIN`: la ampliación de
dominio físico es necesaria antes de habilitar el candidato. Se conserva tanto
el log inicial fallido como el recheck; no se reemplazó el primero por un PASS.
