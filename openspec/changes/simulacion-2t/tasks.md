# Tareas de simulacion-2t

## Definición documental previa
- [x] 1. Comprobar Git/código/documentación pertinente y preservar entrega 4 y evidencias.
- [x] 2. Proponer un solo modelo físico, ecuaciones, conductos/transferencias y fuentes primarias.
- [x] 3. Fijar caso sintético completo, datos reutilizados/adicionales y límites de capacidad.
- [x] 4. Definir controles independientes y prueba futura con tolerancias, convergencia y presupuestos previos.
- [x] 5. Revisar puntualmente consistencia documental, validar OpenSpec y actualizar referencias de estado.
- [x] 6. Preparar commit documental propio y registrar publicación pendiente sin reintento de autenticación.

## Prototipo aprobado y autorizado por orden explícita del 15/09/2026
- [x] 7. Obtener aprobación explícita de reducción 0D sin ondas/inercia, transferencias sin almacenamiento y restantes aproximaciones/caso/protocolo de design.md.
- [x] 8. Obtener autorización de implementación/ejecución del prototipo acotado; no se infiere de esta definición.
- [x] 9. Tras autorización, implementar y comprobar balances/enlaces/energía con referencias elementales independientes.
- [x] 10. Tras autorización, ejecutar el caso completo y comparación de resolución, medir coste y registrar convergencia/fallo.
- [x] 11. Diagnosticar localmente el rechazo preservando la serie; comprobar cuadratura, reconstruir una vuelta e identificar si requiere corrección o decisión numérica.
- [x] 12. Implementar la duplicación adaptativa autorizada con perfiles A/B/C y comprobar el intervalo local, retorno físico y controles del integrador.
- [x] 13. Ejecutar una serie A/B/C acotada desde los estados originales, registrar coste/precisión y detener sin extender presupuestos.
- [x] 14. Implementar la variante exterior autorizada de 100/50 Pa, conservar ley original y comprobar transporte, empalme y diagnóstico local con retorno físico.
- [x] 15. Ejecutar el ensayo integrado condicional autorizado y registrar resultados, omisiones, coste, revisión y commit propio.
- [x] 16. Añadir ejecución individual B/100 Pa sin Qt y resultados separados, vinculados y validados para reapertura.
- [x] 17. Integrar pestaña del caso de referencia, QProcess, progreso, cancelación/cierre y gráficos sin afectar proyectos.
- [x] 18. Comprobar consola/interfaz/referencia B, errores/reapertura y Windows visible al 150 %, con captura real.
- [x] 19. Registrar pruebas finales, revisión puntual, estado y commit propio del tramo gráfico.

La orden de ese tramo autorizó tareas 16–19 para el caso fijo, no para motores del
editor ni otras entregas. Aprobar documentos no acredita implementación o pruebas.

## Geometría del editor autorizada — 15/09/2026
- [x] 20. Adaptar copia del editor, validación conjunta/del hijo, topología por función y geometría/inventarios sin cambiar física ni JSON v5.
- [x] 21. Integrar dos orígenes, procedencia/resultado v2 y aviso de configuración anterior; comprobar entradas, archivos y cancelación antes de ejecuciones completas.
- [x] 22. Ejecutar únicamente A/B desde editor y C de contraste de consola, dentro de presupuestos; registrar igualdad con referencia, cambio de cámara y contraste B/C.
- [x] 23. Comprobar recorrido Windows/captura, pruebas finales y revisión puntual; actualizar estado y crear commit propio sin publicar ni archivar.

## Evidencia de esta definición — 15/09/2026
Inicio main 545685b, árbol limpio y un commit por delante de origin/main.
Commit de entrega 4 conservado; publicación sigue pendiente por autenticación
conocida. No se repite push ni se consultan credenciales. Solo documentos: no
pruebas anteriores repetidas, solver, simulaciones, nuevas capturas o curvas.
Fuentes, caso y protocolo constan únicamente en design.md. Implementación y
aceptación manual previas permanecen separadas e intactas.

- Revisión documental independiente puntual: detectó posible rechazo sistemático
  de etapas RK4 cerca del fin del aporte al integrar F_C. Corregido en el diseño:
  evaluación analítica de F_C en todas las etapas del intervalo cerrado, conversión
  por diferencia analítica, sin recorte/renormalización. No se implementó ni probó
  ese algoritmo; autorrevisión del principal de la aclaración y del diff documental.
- Sustitución aritmética independiente para revisar referencias del documento:
  beta_crit=0.5282817877171742, q_sónico=0.04667117121212454 kg/s y
  q(beta=0.8)=0.038214552836718804 kg/s; volúmenes sintéticos coherentes.
  Esto no es una prueba del motor ni evidencia de viabilidad del solver.
- OpenSpec status/instructions/validate disponibles, sin reinstalar ni init/update.
  Validación estricta aprobada; status completo describe artefactos documentales,
  no implementación. Aprobaciones y tareas futuras 7–10 permanecen sin marcar.
- Solo archivos documentales propios preparados para commit separado. Sin cambio
  de código/tests/JSON, ejecución de suite previa ni nuevo intento de publicación.

## Evidencia del prototipo autorizado — 15/09/2026

- Inicio `main` en `6e29745`, árbol limpio, igual a la referencia local
  `origin/main`. Se preservaron entregas anteriores y remoto existente.
  La orden explícita de la usuaria acredita tareas 7/8; no es aprobación inferida
  desde documentos ni aceptación experimental del modelo.
- Implementación: tres módulos estándar (`simulation_case`, `simulation`,
  `prototype`), geometría y área rectangular reutilizadas. Caso sintético separado,
  cuatro CV, seis enlaces reversibles, RK4/eventos, F_C analítica en cada etapa,
  conversión por primitiva, trabajo C/K separado. Sin cambios de Qt, JSON v5,
  dependencias o configuración global. Salidas grandes excluidas de Git.
- Antes de integrar el motor: seis controles elementales independientes aprobados
  en 0,036 s (geometría, orificio, recipientes, adiabática, calor, mezcla). Durante
  preparación, una aserción de CSV exigía igualdad binaria con 140000 Pa y recibió
  139999,99999999997; corregida la aserción numérica, no el resultado ni el modelo.
- Revisión independiente puntual, solo lectura: detectó tendencia exigida incluso
  por debajo de los pisos de sensibilidad. Corregida **antes de la serie** con los
  pisos previos de 1 J y 1e-7 kg, cubierta por reproducción específica. No se añadió
  tolerancia de p/Y. Sin otros defectos concretos en la pasada. El revisor no
  ejecutó el motor; principal realizó autorrevisión y pruebas de la corrección.
- Quince controles nuevos aprobados antes de la serie. Incluyen cancelación real
  programada a los 0,05 s y comprobación de salida en menos de 1 s desde la solicitud,
  retorno inicial C→K con entalpía/fresca del cilindro, cierre, seis evaluaciones de
  enlace por etapa, dominio sin recorte, auditoría con error inducido, presupuestos
  y proceso de consola sin PySide6 importado.
- Una única serie completa, sin reinicios ni cambios posteriores de parámetros,
  método o umbrales. Comando ejecutado desde la raíz:
  `.\.venv\Scripts\python.exe -m motorsim.prototype --output results/simulacion-2t/viabilidad-20260915`.
  Los tres arranques son idénticos, 180°, 3000 rpm. Todas las corridas terminaron
  por **límite de 30 ciclos, no convergido**; ninguna excedió tiempo, RAM, RHS o
  dominio. Rechazos controlados: 2, 1 y 0, respectivamente, sin reparar estados.

| Paso | Ciclos / convergencia | Tiempo | Pico proceso | W_C / W_K [J] | p_C máxima [Pa] |
| --- | --- | --- | --- | --- | --- |
| 0,5° | 30 / No | 5,094 s | 24,6992 MiB | 16,634690 / −3,373391 | 1335402,759 |
| 0,25° | 30 / No | 10,016 s | 28,5313 MiB | 16,544720 / −3,368888 | 1332998,623 |
| 0,125° | 30 / No | 19,125 s | 33,4297 MiB | 16,483385 / −3,366819 | 1331368,705 |

Diagnósticos de la última vuelta; no son resultados convergidos aceptados.
Máximos normalizados entre los cuatro CV y el balance global de esa vuelta:

| Paso | Discreto masa / energía / fresca | Independiente masa / energía / fresca |
| --- | --- | --- |
| 0,5° | 2,10e-15 / 8,21e-16 / 1,07e-15 | 0,113369 / 0,112205 / 0,113119 |
| 0,25° | 1,97e-15 / 1,35e-15 / 2,11e-15 | 0,058870 / 0,058285 / 0,058716 |
| 0,125° | 2,73e-15 / 2,69e-15 / 5,89e-16 | 0,030091 / 0,029804 / 0,030002 |

- **Primer impedimento:** cuadratura independiente fuera de 0,001 desde la primera
  vuelta en las tres resoluciones. No aprueba ninguna vuelta; por eso no se alcanza
  el criterio completo de convergencia aunque m/U/Y/trabajo/presión se estabilicen.
  La cuadratura usa extremos de **cada paso aceptado**, no los pesos RK4 ni solo
  los nodos de 0,5° exportados. Incluye integral independiente de p dV y primitiva
  del calor. El cierre discreto no se presenta como segunda prueba independiente.
- Diagnóstico leído de CSV, sin otra corrida: con falda cerrada a 200°, I permanece
  cerca de 100090,45 / 100022,52 / 100005,60 Pa según resolución y sus caudales de
  extremo muestreados son −0,003580 / −0,001776 / −0,000882 kg/s. Esto muestra una
  discrepancia numérica cerca del equilibrio del reservorio; no se cambia el método
  ni se declara estable por la sola repetición entre vueltas.
- Sensibilidad: **no acreditada**, falta la condición previa de las tres resoluciones
  convergidas. No se fuerza trabajo positivo ni se interpreta como potencia al eje.
  F_s final = 4,69561e-5 / 4,67087e-5 / 4,65400e-5 kg; Q = 37,56490 / 37,36698 /
  37,23197 J. Hay aporte prescrito, pero no una predicción de combustión.
- Serie total medida: 34,719 s; Intel Core i5-10400 @ 2,90 GHz, 12 procesadores
  lógicos, Windows 10.0.19045 AMD64, Python 3.11.0. Pico residente de proceso Windows
  incluye runtime/resultados anteriores de la serie. Avance por vuelta y también
  a intervalos de 0,5 s; cancelación/presupuesto comprobados en cada paso.
- Evidencia local: `results/simulacion-2t/viabilidad-20260915/`, con manifiesto completo,
  entorno, resumen de serie, resúmenes de 30 ciclos por resolución y últimas dos
  vueltas (1442 filas/CSV). Incluye inventarios, P-V, flujos/sentidos, calor, trabajo,
  residuos absolutos y normalizados y causas de parada. No es formato de proyectos.
- Estado final del código, después de la última corrección funcional:
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`:
  **100/100 aprobadas en 8,547 s**; widgets `offscreen`, no inspección visual Windows.
  OpenSpec estricto aprobado. No hay nueva aceptación manual ni validación experimental.
- Tareas 9/10 acreditan implementación, controles y **registro de un fallo de
  viabilidad**. Entrega 5 sigue **En curso**, sin integración Qt; no se archiva ni
  inicia entrega 6. Se detiene la prueba; resolver el impedimento mediante cambios
  de método/modelo o una nueva campaña requiere decisión posterior.
- Código, caso, pruebas y documentación se preparan en commit propio. Se permite
  un único push normal según la orden actual; su resultado se comunica en la entrega,
  sin buscar credenciales, cambiar remotos/configuración ni reescribir historial.

## Diagnóstico localizado posterior — 15/09/2026

Inicio en `54821600bd46b034cd15f8d88ae8b5be066c48c7`, rama main, árbol limpio,
un commit por delante de la referencia origin/main. Commit y archivos de
`results/simulacion-2t/viabilidad-20260915/` preservados; se compararon SHA-256
antes/después y se registraron en el diagnóstico. No se hizo push ni se tocó
autenticación. La orden actual autoriza diagnóstico y correcciones demostradas,
no cambios silenciosos de método, modelo, tolerancias o presupuestos.

### Condición que falla, sin cambiar la aceptación

Se leyeron los 30 resúmenes existentes por resolución. Las métricas de
repetibilidad alcanzan tres vueltas seguidas desde la vuelta 8 / 9 / 9 para
0,5° / 0,25° / 0,125°, respectivamente. Esto **no es convergencia completa**:
`balances_passed=False` en las 30 vueltas de cada una, por auditoría independiente
>0,001; `convergence.passed` sigue False y el contador compuesto permanece en cero.
Ni el calor positivo ni la repetibilidad sustituyen ese requisito.

En la última vuelta, máximos entre resoluciones: diferencia relativa m=3,35e-6,
U=3,17e-7, Y absoluta=1,27e-6, W relativa=5,70e-6 y curva p relativa=2,13e-6;
todos cumplen sus respectivos límites de repetibilidad. Los balances siguen
rechazados según la tabla original de esta tarea, que no se modifica.

Sensibilidad diagnóstica entre finas: W=0,0037073 relativo, p máxima=0,0012242,
curva=0,0014002, máximo por enlace de masa=0,0033007 (todos <0,01), pero
**Delta Y_E=0,0089694048 >0,005**; Y_I/K/C=0,00168946 / 0,00077414 / 0,00050642.
La diferencia gruesa Y_E=0,0168160 es mayor, pero la tendencia favorable no
satisface el límite fino. Comparaciones diagnósticas, no acreditación formal:
faltan las tres resoluciones convergidas. No se forzó esa condición al calcularlas.

### Cuadratura, tiempos y trazabilidad

- Antes del replay, cinco pruebas de flujos prescritos aprobaron: constante,
  lineal con inversión y distintos donantes, integral cuadrática y su error
  de trapecio conocido, eventos no uniformes, extremos repetidos de duración
  cero y conversión grados/18000 a segundos. Un signo de transporte incorrecto
  inducido sigue siendo rechazado. No se usan valores esperados del propio auditor.
- Una sexta prueba fuerza el descarte de un intento calculado y comprueba que
  ni el libro RK4 ni el auditor incorporan ese intento. Se acepta solo el medio
  paso posterior, con el mismo inventario/libro que su cálculo separado.
- El auditor original evalúa extremos de **todos los pasos aceptados**. Cambiar
  solo la información usada, reconstruyendo desde el CSV de 0,5°, da máximos
  0,113440 / 0,058788 / 0,029994, frente a 0,113369 / 0,058870 / 0,030091 del
  auditor de pasos aceptados. La escasez de nodos CSV no explica el rechazo.
  No se interpoló una salida ni se sustituyó el auditor por pesos RK4.
- Replay de **una única vuelta**, la 30 de 0,5°, desde el estado guardado al final
  de la 29, a los ángulos originales 10620–10980°. No es un arranque formal ni
  un mecanismo de checkpoint. Reproduce **exactamente** estado final y auditoría
  originales: 728 pasos aceptados, 16 no uniformes junto a eventos, cero rechazos,
  duración física total 0,020000000000000167 s. Pasos contiguos, ningún tramo omitido.
- Los cuatro tiempos de etapa y el extremo coinciden con el paso registrado:
  discrepancia angular cero. Pesos [1,2,2,1]/6 frente al incremento del libro:
  diferencias máximas masa/F=6,78e-21 kg, entalpía=3,56e-15 J. **Esto verifica la
  implementación RK4, no es la segunda auditoría independiente.**
- Cero signos de flujo incorrectos. Donante/entalpía/Y de cada etapa y extremo
  concuerdan: diferencias máximas h relativa=5,68e-16, Y absoluta=1,12e-16.
  Los estados y flujos registrados son contemporáneos. Los 721 nodos de cada
  vuelta CSV son estrictamente crecientes; la frontera compartida entre vueltas
  no agrega un intervalo temporal. La auditoría no se construye desde ese CSV.

### Causa demostrada y descomposición

La discrepancia principal procede de los enlaces exteriores: I cuando la falda
está cerrada (180–270° y 450–540° en esta vuelta), E cuando el escape del cilindro
está cerrado (270–450°). El registro local contiene los seis enlaces por bandas
de 30°. Dos bandas aisladas, sin calor ni trabajo en el CV, permiten comparar
directamente inventario y entrada neta (signo positivo hacia el CV):

| CV / intervalo | Magnitud | Delta inventario | Integral RK4 neta | Trapecios independientes netos |
| --- | --- | --- | --- | --- |
| I / 180–210° | masa kg | +1,668394e-7 | +1,668394e-7 | −5,955713e-6 |
| I / 180–210° | energía J | +3,604604e-5 | +3,604604e-5 | −2,049855 |
| I / 180–210° | fresca kg | +2,043372e-7 | +2,043372e-7 | −5,906428e-6 |
| E / 300–330° | masa kg | +8,499085e-8 | +8,499085e-8 | −1,751367e-6 |
| E / 300–330° | energía J | +4,836327e-6 | +4,836327e-6 | −1,030669 |
| E / 300–330° | fresca kg | −5,856707e-7 | −5,856707e-7 | −7,638749e-7 |

En toda la vuelta, diferencia RK−trapecio del enlace exterior I: +3,762690e-5 kg,
+12,605984 J, +3,754939e-5 kg fresca. En enlace E→exterior: −1,116628e-5 kg,
−6,268392 J, −1,060118e-6 kg fresca. Signos de enlace fijos según el diseño.
La demostración no atribuye el error al calor prescrito del cilindro.

A 200–200,5°, I: Delta p de etapas = +90,4507 / −100,0414 / +287,2195 /
−588,5336 Pa; extremo aceptado +90,4572 Pa. Caudal exterior→I = −0,00357975 /
+0,00382914 / −0,00637686 / +0,00926221 kg/s; extremo −0,00358001.
A 300–300,5°, E: Delta p = +13,3280 / −15,3785 / +43,2213 / −90,0630 Pa;
extremo +13,3283 Pa. Caudal E→exterior = +0,00105017 / −0,00116345 /
+0,00189106 / −0,00281439 kg/s; extremo +0,00105020.

Las etapas de entrada a E transportan h=553500 J/kg e Y=0 del reservorio;
las de salida usan T/Y de E. La elección es correcta para esos estados auxiliares,
pero el paso fijo provoca retornos numéricos que alteran el resultado aceptado.
Las etapas 2/3 comparten tiempo; no son muestras sucesivas de una trayectoria densa.

**Error de trayectoria demostrado:** E aislado del cilindro, sin calor/trabajo,
p inicialmente superior al exterior, debe descargar hacia equilibrio conservando
Y. Sin embargo, el paso de 0,5° eleva ligeramente p y reduce Y_E. El mismo intervalo
de 0,5° se comprobó con dos discretizaciones, desde exactamente el mismo estado:

| Diagnóstico 300–300,5° | Pasos | p_E final −100000 [Pa] | Cambio Y_E (referencia: cero) |
| --- | --- | --- | --- |
| RK4 0,5° | 1 | +13,328288 | −0,00015287985 |
| RK4 0,125° | 4 | +0,885767 | −0,00002690636 |

Refinar **la integración** reduce el defecto de trayectoria, no lo elimina ni
acredita la serie. Refinar solo la salida de auditoría prácticamente no cambia
su fallo. No se realizó una escalera ni un nuevo barrido de casos/resoluciones.

### Resultado, coste y parada

- No se encontró defecto de implementación o cuadratura que corregir. El núcleo,
  parámetros, método, tolerancias y aceptación compuesta permanecen idénticos a
  54821600. Se añaden controles de diagnóstico, no una corrección física disfrazada.
  No hay serie oficial posterior: la repetición autorizada estaba condicionada a
  una corrección demostrada. Los resultados anteriores siguen no acreditados.
- **Única propuesta pendiente:** control local RK4 por comparación de un paso
  con dos medios pasos, detallado en design.md, sin implementarlo. 12 RHS frente
  a 4 por intento, más pasos/rechazos cuando se refine; tolerancias locales por
  fijar/aprobar. No garantiza coste/precisión ni autoriza superar mínimos/topes.
- Replay: 0,219 s, 40,77 MiB, 2912 RHS, una vuelta. Intervalo adicional: cinco
  pasos en total, 20 RHS; su `seconds=0.0` significa inferior a la resolución
  del reloj utilizado, **no coste físico nulo**. El proceso que cargó la traza y
  ejecutó ese intervalo duró 0,793 s (herramienta), pico 60,13 MiB. Equipo/versiones
  iguales a la evidencia inicial. Sin exceder los presupuestos del protocolo.
- Archivos nuevos locales: `results/simulacion-2t/diagnostico-20260915/`,
  `diagnosis.json`, `accepted-steps.json`, `closed-interval.json`, `trace-checks.json`.
  Script reproducible de diagnóstico fijo en `tests/diagnose_simulation_balance.py`;
  no telemetría general ni salida sobrescrita. Los resultados quedan excluidos de Git.
- Suite pertinente final: `.\.venv\Scripts\python.exe -m unittest discover -s tests
  -p 'test_simulation_*.py' -v`: **21/21 aprobadas en 0,275 s**. Incluye seis controles
  nuevos y quince previos. No se repite Qt/persistencia: producción e interfaz no
  cambiaron. OpenSpec estricto aprobado. Sin nueva inspección visual ni aceptación manual.
- Revisión puntual independiente de solo lectura: sin hallazgos bloqueantes;
  confirmó evidencia de error de trayectoria y precisó cómo informar el reloj del
  ensayo corto. Autorrevisión del principal de la instrumentación, comprobación
  posterior de pesos/tiempos/donantes, documentación y preservación de resultados.
- Entrega 5 **En curso: decisión numérica pendiente**. Se prepara commit documental,
  de pruebas e instrumento localizado; no hay reintento de publicación, archivo de
  cambio, integración Qt ni avance a otra entrega.

## Evidencia del ensayo adaptativo autorizado — 15/09/2026

Esta evidencia corresponde a las tareas 12/13 y no modifica los resultados
históricos anteriores. Inicio en `main`, `783970d90d8470d1f552dbdf11b7781133ea6915`,
árbol limpio e igual a la referencia local `origin/main`. Commit y directorios
originales conservados; sus SHA256 se comprobaron antes y después del ensayo.
Sin push, consulta de credenciales ni cambios de configuración global.

### Implementación y regresión local

`motorsim/adaptive.py` conserva los dos medios pasos, sin Richardson; compara
individualmente los doce componentes m/U/F con el estimador /15 y los perfiles
fijos de design.md. Control proporcional 0,9 y exponente 1/5, factor 0,2–2,
tratamiento explícito de cero/no finitos y reducción en cada rechazo. Cada rama
mantiene sus acumuladores; F_s se captura fuera de los intentos, F_C continúa
analítica. Auditoría independiente en ambos medios pasos aceptados, incluido el
punto intermedio. Eventos y exportación común a 0,5° no sustituyen esos pasos.
Se cuentan también las evaluaciones de extremos que calculan RHS: normalmente
15 por intento (12 etapas y 3 extremos), más el inicio de cada ciclo; un intento
interrumpido puede costar menos. El presupuesto cuenta todas esas evaluaciones.
El mínimo 0,001° se exige a cada medio paso, sin tolerancia física artificial.

Intervalo 300–300,5° desde el estado literal de la evidencia anterior, sin
alterarlo ni alimentar la serie formal con él. Resultado local:

| Método | Cambio Y_E | RHS reales | Tiempo s |
| --- | ---: | ---: | ---: |
| Fijo histórico 0,5° | −0,000152879850 | 4 etapas históricas | — |
| A | −0,000011022007 | 121 | 0,006279 |
| B | −0,000006908630 | 136 | 0,006230 |
| C | −0,000004036773 | 196 | 0,008000 |

La deriva disminuye aproximadamente 13,9/22,1/37,9 veces; no desaparece.
Todos completan el intervalo sin agotar límites. El ensayo separado con presión
inicial de E inferior al reservorio admite entrada física; no se anulan flujos
ni se impone Y. Comparación local completa, con presión, m/U/F/Y y masa en ambos
sentidos: `results/simulacion-2t/adaptativo-local-20260915/comparison.json`.
`summary-final.json` contiene el conteo corregido; sustituye al conteo inicial
de `summary.json`, que se conserva con sus hashes de las fuentes originales.

### Única serie formal y coste

Comando ejecutado una vez:
`.\.venv\Scripts\python.exe -m motorsim.prototype --output results/simulacion-2t/adaptativo-20260915`.
Cada perfil parte del caso original S2T-0D-01; no hay continuación entre perfiles.
Python 3.11.0, Windows 10.0.19045 AMD64, Intel i5-10400 a 2,9 GHz, 12 CPU lógicas;
Qt no cargado. Parámetros y entorno completos en `case.json`/`environment.json`.

| Perfil | Convergencia completa | Ciclos completos (+ parcial) | Parada | s | Pico MiB |
| --- | --- | ---: | --- | ---: | ---: |
| A | No | 18 (+19) | 60 s por ejecución | 60,000 | 26,207 |
| B | No | 11 (+12) | 60 s por ejecución | 60,000 | 34,262 |
| C | No | 7 (+8) | 180 s globales | 57,015 | 41,828 |

La serie registra 180,110 s incluyendo cierre/escritura final: la integración
se detuvo al alcanzar el tope global, sin extenderla para acabar el ciclo.
Ninguna ejecución llegó a 30 ciclos, 512 MiB o dos millones de RHS. No se lanzó
otra serie ni se modificaron tolerancias para intentar obtener un resultado favorable.

| Perfil | Intentos | Medios pasos aceptados | Rechazos error / físico / no finito | RHS totales (etapas + extremos) |
| --- | ---: | ---: | --- | --- |
| A | 88773 | 177290 | 127 / 1 / 0 | 1331603 (1065268 + 266335) |
| B | 89810 | 179444 | 86 / 2 / 0 | 1347150 (1077712 + 269438) |
| C | 85798 | 171476 | 59 / 1 / 0 | 1286967 (1029568 + 257399) |

| Perfil | Máximo propuesto autorizado ° | Medio paso mínimo ° | Media ° | Máximo real ° |
| --- | ---: | ---: | ---: | ---: |
| A | 0,5 | 0,0010012213 | 0,0385665329 | 0,0887996161 |
| B | 0,25 | 0,0010001903 | 0,0237333965 | 0,0489866740 |
| C | 0,125 | 0,0010001870 | 0,0147747914 | 0,0282873044 |

Los CSV `profile-*-attempts.csv` registran propuesta, medio paso, error, causa y
RHS acumulados de cada intento. Se comprobó sobre ellos E <= 1 y medio paso
>= 0,001° en todos los aceptados, y dos medios pasos por intento aceptado.

### Resultados del último ciclo completo de cada perfil

| Perfil | W indicado C J | W cárter J | p máxima C Pa | Y_I | Y_K | Y_C | Y_E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 16,4349633 | −3,3651205 | 1330075,43 | 0,98550943 | 0,97634931 | 0,56160010 | 0,37569610 |
| B | 16,4807541 | −3,3653063 | 1331281,86 | 0,98573406 | 0,97699551 | 0,56206279 | 0,37779044 |
| C | 16,5977916 | −3,3661354 | 1334390,39 | 0,98667551 | 0,97865857 | 0,56316336 | 0,37962940 |

Residuos independientes normalizados (magnitudes adimensionales; límite 0,001):

| Perfil / volumen | Masa | Energía | Fresca |
| --- | ---: | ---: | ---: |
| A / I | 7,892706e-3 | 7,819416e-3 | 7,867605e-3 |
| A / K | 7,766539e-7 | 1,030596e-6 | 6,605787e-7 |
| A / C | 8,333321e-7 | 6,320002e-7 | 4,184468e-7 |
| A / E | 8,099840e-3 | 7,203279e-3 | 7,813646e-4 |
| A / global | 7,462293e-3 | 9,474212e-3 | 5,022387e-3 |
| B / I | 4,546109e-3 | 4,505227e-3 | 4,531906e-3 |
| B / K | 3,206877e-7 | 4,393231e-7 | 2,657957e-7 |
| B / C | 4,317189e-8 | 3,332466e-8 | 3,719211e-8 |
| B / E | 5,228243e-3 | 4,653139e-3 | 5,215051e-4 |
| B / global | 4,466760e-3 | 5,763218e-3 | 2,903093e-3 |
| C / I | 2,744366e-3 | 2,721198e-3 | 2,736371e-3 |
| C / K | 2,129934e-7 | 2,639108e-7 | 1,951430e-7 |
| C / C | 8,590239e-8 | 6,499510e-8 | 4,440851e-8 |
| C / E | 3,241316e-3 | 2,890752e-3 | 3,309921e-4 |
| C / global | 2,712801e-3 | 3,527325e-3 | 1,748217e-3 |

Fallan I (los tres balances), E (masa/energía) y global (los tres), aunque los
balances discretos máximos son 8,393e-15 / 1,095e-14 / 4,326e-15. El peor
independiente es energía global: 0,947421 % / 0,576322 % / 0,352732 %, superior
al 0,1 % en los tres perfiles. Ningún ciclo satisfizo la aceptación completa.

Comparación diagnóstica a igual fase, pero ciclos distintos (18/11/7):

| Par | Diferencia relativa W | Diferencia relativa p máxima | Diferencia curva p | Diferencias absolutas Y_I / Y_K / Y_C / Y_E |
| --- | ---: | ---: | ---: | --- |
| A–B | 0,00277844 | 0,00090621 | 0,00103254 | 0,00022463 / 0,00064620 / 0,00046269 / 0,00209434 |
| B–C | 0,00705139 | 0,00232955 | 0,00264597 | 0,00094145 / 0,00166306 / 0,00110058 / 0,00183896 |

No acredita sensibilidad: no existen soluciones completamente convergidas y
varias diferencias crecen entre el primer y segundo par. `comparison-diagnostic.json`
incluye los seis enlaces y marca explícitamente esa limitación. Los archivos
`step-*-summary.json` conservan también los estados/balances del ciclo parcial;
`step-*-last-two.csv` y `step-*-partial.csv` separan ciclos completos y parcial.
Todos los resultados nuevos están bajo directorios ignorados de `results/simulacion-2t/`.

### Comprobación final y cierre de este ensayo

- Suite final, tras corregir el conteo y ejecutar la serie:
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_adaptive.py -v`:
  **10/10 aprobadas, 0,138 s**; y
  `.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_simulation_*.py' -q`:
  **21/21 aprobadas, 0,396 s**. Incluyen retorno físico, rechazo local con estado
  positivo, ramas/acumuladores, eventos/calor, mínimo real, RHS/presupuesto,
  auditoría del punto intermedio y cancelación observable.
- Una revisión puntual independiente de solo lectura encontró un subconteo de
  RHS en evaluaciones de extremos. Corregido antes de la serie, con prueba que
  contrasta las llamadas reales a Model.evaluate. Autorrevisión del principal
  de la corrección, documentación y trazas; sin otra campaña de revisión.
- `openspec validate simulacion-2t --strict --no-interactive`: aprobado en el
  estado documental final. `git diff --check`: sin errores de espacios.
- **Controlador:** los controles ejecutados acreditan el comportamiento
  especificado, dentro del alcance probado; el estimador no es una cota garantizada.
- **Defecto local:** reducido, no eliminado; no se impuso invariancia artificial.
- **Viabilidad completa:** no acreditada dentro del protocolo; balances y coste
  impiden cerrar. La entrega 5 sigue abierta, sin validación experimental,
  integración Qt, cambios de JSON, inspección de interfaz, archivo ni otra etapa.
  Commit propio del ensayo; publicación no intentada por instrucción expresa.

## Variante exterior regularizada — evidencia del 15/09/2026

Inicio: `main` limpio en `8d9249496152898e7b0bc92dd5b906d67e1c9c3b`, igual a la
referencia local `origin/main`. No se infiere publicación pendiente desde informes
anteriores; no se consultó autenticación ni se hizo push. Se conservaron todos
los directorios anteriores: hashes SHA256 comprobados antes/después e inventariados
en `results/simulacion-2t/regularizado-local-20260915/summary.json`.

### Implementación y controles locales

Variante candidata exclusiva de los enlaces exteriores 0/5, con banda fija de
100 Pa o 50 Pa. Fórmula/identidad estable y autorización en design.md. El mismo
caudal firmado transporta entalpía/fresca según donante; no hay zona muerta ni
presión/composición impuesta. Interiores y opción original permanecen intactos.
El controlador, sus perfiles, auditoría y criterios originales no se modificaron.

Cinco pruebas nuevas comprueban cero/área cero, sentidos/donantes, transporte,
pendientes laterales finitas cerca de cero (contraste con límite analítico),
continuidad y pendientes en ambos bordes, igualdad exacta fuera de la banda,
ámbito exterior, descarga/llenado y parada condicional mediante un A simulado fallido.
Con T distintas las pendientes laterales de cero son distintas: no se afirma C1 allí.

Intervalo 300–300,5°: perfil A, mismo estado inicial exacto que el registro original
(igualdad de los doce componentes comprobada contra la evidencia guardada).
Los ensayos de llenado son separados y cambian explícitamente la presión inicial
de E a 99986 Pa; no se usaron para iniciar el motor formal.

| Banda Pa / caso | p_E final Pa | m_E final kg | U_E final J | F_E final kg | Delta Y_E | Masa sale / entra kg | RHS |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 100 / descarga | 100001.33273520 | 6.859646831308e-05 | 29.9203287876 | 3.023136743386e-05 | 5.551115123e-17 | 6.094887995e-09 / 0.000000000e+00 | 46 |
| 100 / llenado | 99998.50333283 | 6.860932198777e-05 | 29.9194822324 | 3.023405353131e-05 | -4.341518419e-05 | 0.000000000e+00 / 6.758786693e-09 | 46 |
| 50 / descarga | 100000.53084418 | 6.859606085928e-05 | 29.9200888624 | 3.023118786360e-05 | 0.000000000e+00 | 6.502341802e-09 / 0.000000000e+00 | 61 |
| 50 / llenado | 99999.38166092 | 6.860979677576e-05 | 29.9197450276 | 3.023405353131e-05 | -4.646467156e-05 | 0.000000000e+00 / 7.233574680e-09 | 46 |

Descarga inicial: p_E=100013,328016 Pa, Y_E=0,4407131763092831.
La deriva fija histórica era −1,5287985e-4; con adaptación original A, −1,1022007e-5.
Con ambas bandas queda al nivel de redondeo (5,55e-17 / 0), sin fijar Y; la masa
de retorno en esa descarga es cero calculado, no recortado. El llenado conserva
el retorno físico y mezcla residual del reservorio. Todos los intervalos terminan
sin límites: 0,006372 / 0,004082 / 0,003306 / 0,003620 s en el orden de la tabla;
pico de proceso local 36,38 MiB. Estados, transportes RK/independientes y cada
intento quedan en el resumen local. El éxito local habilitó el ensayo integrado.

### Ejecución integrada única con condiciones de parada

Comando ejecutado desde la raíz:

```powershell
.\.venv\Scripts\python.exe -m motorsim.regularized_trial --output results/simulacion-2t/regularizado-20260915
```

A a 100 Pa convergió; se habilitaron B/C. A/B/C aprobaron convergencia y
sensibilidad; solo entonces se ejecutó C a 50 Pa con 60 s separados. Ningún
ensayo autorizado se omitió por parada. No hubo otras bandas, perfiles ni reinicios.
Todos partieron de los mismos estados originales, con captura analítica de F_C.

| Banda / perfil | Ciclos | Convergencia completa / parada | s | Pico MiB | RHS reales |
| --- | ---: | --- | ---: | ---: | ---: |
| 100 / A | 10 | Sí / tres ciclos consecutivos | 6.500 | 24.820 | 135053 |
| 100 / B | 10 | Sí / tres ciclos consecutivos | 10.735 | 28.668 | 228171 |
| 100 / C | 10 | Sí / tres ciclos consecutivos | 21.609 | 33.223 | 442738 |
| 50 / C | 10 | Sí / tres ciclos consecutivos | 21.312 | 37.520 | 446069 |

Serie principal: 39.282 s incluyendo salidas entre perfiles;
total con comparación adicional: 60.719 s. Cada ejecución <60 s,
serie principal <180 s, proceso <512 MiB y RHS <2 millones por ejecución.
Equipo: Intel i5-10400 a 2,9 GHz, 12 CPU lógicas, Windows 10.0.19045 AMD64,
Python 3.11.0, Qt no cargado. Entorno y parámetros efectivos guardados.

| Banda / perfil | Medios pasos aceptados | Rechazos error / físico / no finito | RHS etapas / extremos | Paso mínimo / media / máximo grados |
| --- | ---: | --- | --- | --- |
| 100 / A | 17662 | 169 / 7 / 0 | 108040 / 27013 | 0.001426757 / 0.203827426 / 0.250000000 |
| 100 / B | 30050 | 182 / 9 / 0 | 182536 / 45635 | 0.002348157 / 0.119800333 / 0.125000000 |
| 100 / C | 58788 | 120 / 2 / 0 | 354184 / 88554 | 0.001167298 / 0.061236987 / 0.062500000 |
| 50 / C | 59160 | 157 / 1 / 0 | 356848 / 89221 | 0.001166432 / 0.060851927 / 0.062500000 |

Las trazas se comprobaron: cada intento aceptado tiene E<=1, dos medios pasos
y mínimo real >=0,001°. Sin reutilización oculta de RHS ni ajuste de tolerancias.

### Balances y resultados del ciclo 10

| Banda / perfil | W_C J | W_K J | p_max C Pa | Y_I / Y_K / Y_C / Y_E |
| --- | ---: | ---: | ---: | --- |
| 100 / A | 16.490611131 | -3.365129402 | 1331523.577278 | 0.985592715 / 0.977132500 / 0.562183783 / 0.381087335 |
| 100 / B | 16.490507512 | -3.365130648 | 1331530.846071 | 0.985594276 / 0.977135016 / 0.562185870 / 0.381089503 |
| 100 / C | 16.490501910 | -3.365130603 | 1331532.407998 | 0.985594642 / 0.977135572 / 0.562186303 / 0.381089919 |
| 50 / C | 16.490662782 | -3.365110671 | 1331536.775280 | 0.985593956 / 0.977136021 / 0.562191817 / 0.381049355 |

Residuos independientes normalizados m/U/F por CV y global (límite 0,001):

| Banda / perfil / CV | Masa | Energía | Fresca |
| --- | ---: | ---: | ---: |
| 100 / A / I | 1.43509702e-07 | 2.14456833e-07 | 1.20198327e-07 |
| 100 / A / K | 6.28985652e-06 | 1.08173059e-05 | 3.75689261e-06 |
| 100 / A / C | 1.32253253e-05 | 1.18321823e-05 | 3.75765317e-06 |
| 100 / A / E | 2.73298688e-06 | 3.98457942e-06 | 4.45378679e-06 |
| 100 / A / global | 8.37222521e-08 | 1.64179601e-06 | 5.00454631e-07 |
| 100 / B / I | 5.64239679e-08 | 8.77363824e-08 | 4.62173138e-08 |
| 100 / B / K | 1.65470043e-06 | 2.94414138e-06 | 9.20761396e-07 |
| 100 / B / C | 4.45965662e-06 | 4.00305735e-06 | 1.07130566e-06 |
| 100 / B / E | 1.97155391e-06 | 2.34300271e-06 | 1.41927904e-06 |
| 100 / B / global | 1.06595022e-07 | 3.07298252e-07 | 2.72206599e-07 |
| 100 / C / I | 2.87861436e-08 | 4.12490682e-08 | 2.49034837e-08 |
| 100 / C / K | 1.40585011e-06 | 2.31155369e-06 | 9.25992184e-07 |
| 100 / C / C | 3.04123401e-06 | 2.17852791e-06 | 1.54591061e-06 |
| 100 / C / E | 4.15564550e-07 | 7.22571644e-07 | 1.22346145e-08 |
| 100 / C / global | 7.68602145e-08 | 1.33712003e-07 | 1.67401115e-08 |
| 50 / C / I | 3.58443616e-07 | 3.79748951e-07 | 3.50032477e-07 |
| 50 / C / K | 1.11538478e-06 | 1.97807971e-06 | 6.40200053e-07 |
| 50 / C / C | 3.04577218e-06 | 2.17455925e-06 | 1.55843933e-06 |
| 50 / C / E | 1.45732100e-07 | 4.40844144e-07 | 1.05555868e-07 |
| 50 / C / global | 1.38587487e-07 | 2.80285321e-07 | 1.02809776e-08 |

En las cuatro ejecuciones los ciclos 8/9/10 cumplen balances y convergencia
compuesta, con F_s y Q positivos. Máximo discreto normalizado del ciclo 10:
3.763349e-15 / 3.010670e-15 / 2.911096e-14 / 2.900381e-14.
No se sustituyó el auditor por acumuladores del integrador; sus flujos corresponden
a la variante evaluada sobre ambos extremos aceptados de cada medio paso.

### Sensibilidad temporal y dependencia de banda

Sensibilidad A/B/C a 100 Pa: aprobada, incluidos umbrales y tendencia decreciente.
Dependencia 100→50 Pa con C: aprobada contra los umbrales existentes; dos soluciones
convergidas. No es refinamiento temporal ni validación experimental.

| Comparación | Delta W relativo | Delta p_max relativo | Norma curva relativa | Delta Y_I / Y_K / Y_C / Y_E | Mayor delta relativo de enlace |
| --- | ---: | ---: | ---: | --- | ---: |
| A-B / 100 Pa | 6.28356710e-06 | 5.45896786e-06 | 2.27614210e-06 | 1.56144941e-06 / 2.51617122e-06 / 2.08714131e-06 / 2.16810076e-06 | 1.68318942e-06 |
| B-C / 100 Pa | 3.39713219e-07 | 1.17303025e-06 | 1.21651802e-07 | 3.65846219e-07 / 5.56657581e-07 / 4.33666712e-07 / 4.15580255e-07 | 1.69873290e-07 |
| C / 100-50 Pa | 9.75531647e-06 | 3.27988024e-06 | 4.12295253e-06 | 6.86472038e-07 / 4.48583540e-07 / 5.51385773e-06 / 4.05638046e-05 | 1.78734606e-06 |

Evidencia completa en `results/simulacion-2t/regularizado-20260915/`: entorno,
resumen global y carpetas `band-100-profile-A/B/C`, `band-50-profile-C`, cada una
con caso/variante/perfil, resúmenes por ciclo, últimos dos ciclos CSV e intentos.
No hubo ciclo parcial. No se sobrescribieron resultados originales; salidas
voluminosas ignoradas por Git. La ley original sigue ejecutable mediante
`python -m motorsim.prototype`, sin ejecutar otra serie original en esta tarea.

### Pruebas finales, revisión y pendientes

Pruebas automatizadas del estado final, posteriores al ensayo:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_regularization.py -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_adaptive.py -q
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_simulation_*.py' -q
```

5/5 en 0,123 s; 10/10 en 0,128 s; 21/21 en 0,258 s: **36 pruebas aprobadas**.
`openspec validate simulacion-2t --strict --no-interactive`: aprobado.
`git diff --check`: sin errores de espacios en el diff final.
Una revisión puntual independiente de solo lectura, antes del ensayo, no encontró
defectos concretos. Autorrevisión del principal de diff, trazas y preservación de
fuentes. Sin campaña adicional, inspección de interfaz ni aceptación manual atribuida.

**Resultado:** viabilidad numérica acreditada para esta variante candidata y este
caso acotado. No se extrapola al modelo original, que conserva su resultado fallido,
ni a calibración física, validación experimental, ondas o sintonía. La entrega 5
sigue abierta por posterior integración, fuera de esta orden. No se integra Qt,
cambia JSON, archiva ni empieza otra entrega. Commit propio; publicación por la
usuaria, sin intentar autenticación.


## Integración gráfica del caso fijo — evidencia del 15/09/2026

Inicio en main limpio, 0cb0c754bdedcd67e39269e77a91f65b562b8e31, igual a la
referencia local origin/main. Commit, ley original y todos los directorios previos
preservados. No hubo publicación, consulta de credenciales ni cambios globales.
La nueva orden autoriza Qt exclusivamente para el caso fijo; no entradas del editor.

### Implementación

- `reference_run.py`: una ejecución de Model/run_adaptive, B/100 Pa, definición
  compartida del caso y límites originales. No importa Qt ni ejecuta la serie.
  Avance JSON por líneas, cancelación Event por stdin/EOF o Ctrl+C en consola.
- `reference_results.py`: entradas efectivas y contrato pequeño manifest/case/
  summary/samples, con unidades, versión e identificador/hashes. Reapertura valida
  estructura, números, dominio, inventarios, balances, secuencia/correspondencia
  y convergencia; no ejecuta contenido. Resultados fuera de proyectos JSON v5.
- `simulation_view.py`: pestaña con parámetros de solo lectura, QProcess sin shell,
  avance real, un único hijo, cancelación y parada de respaldo tras tres segundos.
  Trabajos provienen del núcleo; P-V mantiene el orden temporal y ángulo usa una
  vuelta continua 180–540 grados. Sin curvas de éxito para estados no aceptados.
- Cierre de MainWindow conserva primero la protección del editor; tras autorizarlo,
  cancela y cierra por señal del hijo. No usa waitForFinished ni processEvents en
  producción. Nuevo cálculo limpia datos anteriores; archivo ilegible conserva
  el resultado válido al abrir. Cambiar proyecto/tipo no reasigna el resultado.

### Ejecuciones reales y comparación

Consola, una sola ejecución (no serie):

```powershell
.\.venv\Scripts\python.exe -m motorsim.reference_run --output results/simulacion-2t/integracion-consola-20260915
```

Interfaz, botón Ejecutar mediante automatización visible:

```powershell
.\.venv\Scripts\python.exe tests/verify_reference_windows.py --output results/simulacion-2t/integracion-ui-20260915
```

| Ejecución | Perfil / banda | Ciclos / parada | Integración s | Pico del cálculo MiB | RHS |
| --- | --- | --- | ---: | ---: | ---: |
| Consola individual | B / 100 Pa | 10 / convergencia completa | 11,719 | 24,598 | 228171 |
| Interfaz real | B / 100 Pa | 10 / convergencia completa | 10,719 | 24,445 | 228171 |
| Referencia previa preservada | B / 100 Pa | 10 / convergencia completa | 10,735 | 28,668 | 228171 |

Comparación exacta de entradas consola/interfaz, todos los resúmenes por ciclo
contra la referencia B (no C), RHS y muestras consola/interfaz: iguales. No se
comparó el tiempo como si fuera determinista. La memoria histórica de B incluía
el proceso que ya había ejecutado A; las nuevas son procesos individuales.
Qt no cargado en el hijo, Windows 10.0.19045 AMD64, Python 3.11.0, Intel i5-10400.

Último ciclo idéntico: W_C=16,49050751206088 J/ciclo,
W_K=-3,3651306484080394 J/ciclo, p_max=1331530,846070603 Pa absolutos.
Y_I/K/C/E=0,9855942761818735 / 0,9771350157648919 /
0,5621858698264297 / 0,38108950299160227. Máximo residuo independiente
normalizado=4,459656622212729e-6 (0,000445966 %, límite 0,1 %), masa en C.
Balances discretos/independientes y convergencia compuesta aprobados en ciclos
8/9/10. No se volvieron a comprobar sensibilidad temporal ni bandas: su evidencia
pertenece al ensayo anterior. No se ejecutaron A/B/C formales, otras bandas ni física nueva.

Los dos directorios nuevos conservan entradas/versión, manifiesto, resúmenes,
muestras e intentos. No sobrescriben la referencia previa. Ubicación predeterminada
para uso normal: LOCALAPPDATA/MotorSim/Resultados; `--output` se usó para evidencia
identificable del recorrido, no está codificado en la aplicación.

### Windows visible y captura

Escritorio Default accesible. Automatización visible, no aceptación manual:
se ejecutó el caso desde la pestaña, conservando un proyecto de prueba con nombre,
4T y cambios pendientes. Se verificó que el proyecto no se modifica al calcular,
que no admite ejecución duplicada, conserva el resultado al navegar y reabre sin
recalcular. Cancelación visible mediante botones Ejecutar/Cancelar aprobada sin
parada forzada; manifiesto Cancelado, curvas retiradas y resultado previo reabierto.

```powershell
.\.venv\Scripts\python.exe tests/verify_reference_windows.py --cancel --output results/simulacion-2t/integracion-cancelacion-visible-20260915 --result results/simulacion-2t/integracion-ui-20260915/manifest.json
.\.venv\Scripts\python.exe tests/verify_reference_windows.py --scale 1.2 --suffix=-ajustada --result results/simulacion-2t/integracion-ui-20260915/manifest.json
```

Al 150 % efectivo (devicePixelRatio=1,5; base de escritorio 125 % por factor Qt
1,2 solo del proceso), se inspeccionaron título nativo, parámetros, controles,
foco, texto, curva angular con PMS/PMI, lazo P-V, unidades y limitación. En ancho
compacto los gráficos se apilan y la barra vertical permite consultar ambos,
sin desplazamiento horizontal. Pico observado de interfaz 87,7 MiB, separado
explícitamente del cálculo. El primer encuadre excedía la pantalla; se ajustó
el tamaño de la ventana de comprobación y se repitieron capturas al reabrir el
resultado, sin otra simulación. No se cambiaron políticas ni escalado global.

Capturas reales finales inspeccionadas, sin generar ni editar imágenes:
- `docs/images/motorsim-simulacion-150-ajustada.png`: encabezado, caso y estado.
- `docs/images/motorsim-simulacion-150-resultados-ajustada.png`: ambos gráficos,
  valores, unidades, ruta y memoria/limitación.
- `docs/images/motorsim-simulacion-150-compacta-ajustada.png` y
  `docs/images/motorsim-simulacion-150-compacta-resultados-ajustada.png`: ancho
  compacto y desplazamiento. No se atribuye una ejecución nueva al reabrir.

### Pruebas finales y revisión puntual

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

**134/134 aprobadas en 13,032 s** en el estado final de código. Incluyen 13 controles
nuevos de archivos/integración, los existentes del núcleo y regresiones del editor.
Las pruebas Qt de suite son offscreen; la evidencia visual Windows está separada.
OpenSpec: `openspec validate simulacion-2t --strict --no-interactive` aprobado;
`git diff --check` sin errores de espacios. Importación independiente de
`motorsim.reference_run`: ningún módulo PySide6 cargado.
Cobertura pertinente: inicio, señales de progreso, cancelación cooperativa real,
rechazo de doble ejecución, cierre con Cancelar/Descartar del editor, hijo simulado
sin respuesta detenido de forma acotada, fallo de arranque, salida cero sin resultado,
no convergencia/presupuesto, reapertura, archivos mezclados/faltantes/alterados,
unidades/NaN/tipos/dominio, falso éxito, orden temporal de gráficos e independencia
del proyecto. La suite usa ensayos breves/controlados, no repite la serie formal.

Una revisión independiente de solo lectura encontró dos defectos concretos:
estructura de balances podía lanzar AttributeError y presión máxima negativa
podía pasar. Corregidos con verificación de diccionario, dominio y máximo no menor
al de muestras; añadida regresión. Autorrevisión del principal de correcciones,
resultados/capturas y diff, sin otra campaña de revisión.

Viabilidad numérica del caso: ya acreditada para la variante. Integración gráfica
del caso fijo: comprobada ahora. Aceptación manual de la usuaria: no atribuida.
Uso con motores editados: pendiente de definición y comprobación, fuera del tramo.
Entrega 5 sigue En curso. No se archiva ni comienza entrega 6. Commit propio;
la publicación queda a cargo de la usuaria, sin reintentar autenticación.

## Conexión del editor — evidencia del 15/09/2026

Inicio de este tramo: main en 379cf7fab0e085a39031246306508fa662b88c79, limpio y
alineado con la referencia origin/main disponible. Commit e historia preservados;
sin fetch/push, credenciales ni cambios globales. La orden amplía exclusivamente
el caso admitido con entradas del editor. Los estados históricos anteriores
permanecen como evidencia de sus respectivas etapas, no como pendientes actuales.

### Implementación y controles previos

`project_case.py` adapta la copia v5 al mismo Model y condiciones de SyntheticCase,
sin mutarlo ni modificar sus ecuaciones. Preflight conjunto y repetido en hijo:
dominio monocilíndrico 2T, falda, lumbreras/continuidad y cierre analítico 350–390°.
Lumbreras por función, escape→enlace 4, transferencias canonizadas→2/3; mapeo con
filas originales conservado. Volúmenes/áreas/eventos e inventarios iniciales se
derivan de la geometría capturada; metadata no determina topología.

GUI conserva ejecución/cancelación/cierre y añade dos orígenes, comprobación,
copia independiente sin guardar, detalle efectivo y aviso de configuración
anterior. Captura inválida bloquea antes de crear QProcess, reúne errores de
ficha, lumbreras, admisión y conductos. No sustituye texto inválido por valores
anteriores ni cambia dirty/JSON. Resultado v2 conserva procedencia y copia, con
reconstrucción estricta del contrato; muestras verificadas contra volúmenes/flujos
del modelo. Resultado v1 preservado y reabierto sin integrar. C solo consola.

Antes de A/B/C: **12 pruebas nuevas de adaptación/Qt + 6 de lector + 7 de ejecución
asíncrona aprobadas**. Cubren edición válida con coma/sin guardar, copia inmutable,
ausencias/múltiples errores, dominio/cierre, todas las dimensiones de ficha,
lumbreras, falda y tramos, orden/nombres, inventarios iniciales, referencia intacta,
contrato alterado coherente pero muestras de otra geometría, procedencia/reapertura
sin archivo original, aviso al editar/abrir otro proyecto y cancelación real breve.
Regresiones previas comprueban cancelación/cierre/arranque/archivos/errores. Ninguna
de estas pruebas es otra ejecución completa o campaña física.
Se actualizó un fixture antiguo de muestras estáticas a volúmenes/estados
coherentes con cada ángulo para mantener su prueba de máximo inferior a muestras
con la validación geométrica nueva; no se relajó el lector.

### Tres ejecuciones completas autorizadas

```powershell
.\.venv\Scripts\python.exe tests/verify_project_simulation_windows.py --output results/simulacion-2t/editor-20260915 --scale 1.2 --suffix=-150
```

El recorrido crea únicamente archivos propios de prueba, carga A/B mediante
Abrir del editor y acciona Comprobar entradas/Ejecutar. A tiene geometría exacta
de referencia. B carga una copia y cambia solo compresión 8→8,2 sin guardar.
C usa en consola la copia efectiva de B, --project-input request-C.json y
--profile-c-check, idénticas condiciones salvo el perfil autorizado. QProcess
del motor y consola no cargaron PySide6 (`qt_loaded=false` en los tres entornos).

| Ejecución | Perfil / banda | Ciclos / parada | Integración s | Pico cálculo MiB | RHS |
| --- | --- | --- | ---: | ---: | ---: |
| A, geometría de referencia por editor | B / 100 Pa | 10 / tres ciclos convergidos | 10,625 | 24,602 | 228171 |
| B, solo compresión 8,2 por editor | B / 100 Pa | 9 / tres ciclos convergidos | 9,500 | 25,008 | 205937 |
| C, misma geometría modificada por consola | C / 100 Pa | 9 / tres ciclos convergidos | 18,953 | 24,938 | 398518 |

Integración total **39,078 s**; pared hasta escribir contraste **42,828 s**,
incluidos arranque/reapertura y escritura, antes de capturas. Sin ampliar 60 s,
30 ciclos, memoria/RHS/paso/rechazos/dominio ni el tope global de 180 s. No hubo
otras bandas, barridos, búsquedas o repeticiones de cálculos completos.

A coincide **exactamente** en todos los ciclos, muestras y RHS con
`integracion-ui-20260915`, referencia B/100 preservada. No se exige igualdad de
tiempo/memoria. Cámara A=18,32176835573567 cm³; B=17,81283034585413 cm³.
Copias B/C idénticas; procedencia B conserva nombre/ruta de PRUEBA y dirty=true,
sin reescribir el proyecto guardado con compresión 8.

| Último ciclo | A | B | C |
| --- | ---: | ---: | ---: |
| W_C J/ciclo | 16,49050751206088 | 16,63155294204956 | 16,63154753895948 |
| W_K J/ciclo, diagnóstico | -3,3651306484080394 | -3,3652474266840153 | -3,3652476358359698 |
| p máxima Pa absolutos | 1331530,846070603 | 1366927,2751548453 | 1366927,1375845007 |
| Y_I | 0,9855942761818735 | 0,9858254226456079 | 0,985826021439556 |
| Y_K | 0,9771350157648919 | 0,9775046102019959 | 0,9775055462136528 |
| Y_C | 0,5621858698264297 | 0,5627356966320124 | 0,5627364649506077 |
| Y_E | 0,38108950299160227 | 0,3819618593595342 | 0,38196250068608123 |
| Peor balance independiente, % | 0,000445966 | 0,000454996 | 0,000296730 |

Todos los balances discretos/independientes y convergencia compuesta aprobados.
Contraste **B/C de compresión 8,2**, soluciones convergidas de ciclo 9: diferencias
normalizadas W=3,2486984813e-7; pmax=1,0064204655e-7; curva=1,1580874646e-7;
máxima de seis enlaces=1,8967979819e-7 (límite existente 0,01 con pisos vigentes).
Diferencias absolutas Y_I/K/C/E=5,9879394809e-7 / 9,3601165696e-7 /
7,6831859530e-7 / 6,4132654704e-7 (límite 0,005). Contraste aprobado, no evidencia
de tendencia con tres perfiles ni de validez/calibración de todo el dominio.

Artefactos locales nuevos preservados en `results/simulacion-2t/editor-20260915/`:
A/B/C con manifest/case/summary/samples/attempts, proyectos de prueba A/B,
request-C.json, console-C.log y protocol.json con valores/métricas sin redondear.
No se incluyen proyectos personales ni se sobrescribe evidencia previa. Los
resultados numéricos siguen ignorados por Git; se versionan código/documentación
y las capturas reales, sin .venv ni cachés.

### Windows, pruebas finales y cierre

Escritorio Default accesible. Automatización con ventanas reales, al 150 % efectivo
(base 125 %, QT_SCALE_FACTOR=1.2 solo en proceso). Proyecto y estado pendiente
conservados tras ejecutar y reabrir, doble inicio rechazado, navegación entre
secciones, foco por Tab y ancho compacto sin desplazamiento horizontal comprobados.
Inspección de capturas por el principal: identidad de PRUEBA/compresión 8,2/dirty,
estado convergido/coste/trabajos/balances legibles; presión-ángulo continua y P-V
con unidades, ruta y limitación visibles al desplazar. Título Windows preservado.
No se cambió escalado ni política global. Pico de interfaz observado 104,3 MiB,
separado de los 25,008 MiB del cálculo B.

- `docs/images/motorsim-proyecto-0d-resultado-150.png`: proyecto y resultado real B.
- `docs/images/motorsim-proyecto-0d-curvas-150.png`: gráficas calculadas y diagnóstico.
- `docs/images/motorsim-proyecto-0d-compacto-150.png`: ancho compacto/foco visible.

Suite final `.\.venv\Scripts\python.exe -m unittest discover -s tests -q`:
**146/146 aprobadas en 12,167 s**. Las pruebas Qt de suite son sin pantalla,
distintas del recorrido visible. OpenSpec estricto aprobado. Revisión independiente
puntual de solo lectura sin defectos reproducibles; ejecutó únicamente los 12
tests nuevos (1,531 s), sin cálculos completos. Autorrevisión del principal del
diff final, mediciones y capturas; no se abrió otra campaña de revisión.

**Entrega 5 implementada para este alcance acotado**: editar motor admitido,
comprobar, ejecutar, consultar, guardar y reabrir con procedencia acreditados.
Aceptación manual de la usuaria pendiente y separada; no se atribuye. No hay
otros criterios técnicos pendientes de este tramo. Condiciones editables, ondas,
barridos y modelos ampliados no son requisitos nuevos de cierre. Sin archivo del
cambio ni entrega 6. Commit propio; publicación a cargo de la usuaria, sin intentar
autenticación ni modificar configuración global.
