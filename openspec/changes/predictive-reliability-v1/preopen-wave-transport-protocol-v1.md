# Transporte bajo ondas existentes antes de abrir el escape

2026-10-27. Diagnóstico acotado; no campaña periódica ni ejecución41. Fuente
nativa38, arco0–60° de la trayectoria39 existente (13680→13740°). Sin cambios
de física, geometría, combustión, CFL.4, detector, tolerancias, MUSCL, HLLC,
acoplamiento V2 ni salida. rc7 intacta. El marcador material cambió aguas
arriba con ambas referencias P0/P1; se investiga su transporte bajo ondas.

## Aislamiento y condición inicial

La posición del pistón es monótona0–60° y queda9.363893mm antes del techo
de escape más bajo con válvula totalmente levantada; su recorrido positivo
sólo cierra más. La geometría efectiva0/15/30/45/60° confirma área cero.
Verificar también flujo izquierdo del escape cero en cada stage. Un flujo
no nulo invalida el aislamiento; no modificar la válvula para conseguirlo.

`preopen-wave-transport-v1/preparation-verified/` contiene88/176/352(P0) y
176(P1), medias conservativas, campos/contraste subcelda, admisibilidad,
restauración en constructor nuevo, reloj13680°/fase0° y eventos conservados.
P1 es una hipótesis subcelda, no información física recuperada. El detector
no interviene en este ensayo parcial. Fuente, dependencias y hashes ligados.

## Casos y límites previos a la ejecución

|Caso|Celdas totales|Cap angular|Propósito|
|---|---:|---:|---|
|P0-88|88|.0625°|Comparar con fases/flujos originales39 guardados|
|P0-176|176|.0625°|Evolución espacial con condición física común|
|P0-352|352|.0625°|Tercer nivel espacial|
|P0-176 temporal|176|.03125°|Error temporal independiente|
|P1-176 condicional|176|.0625°|Separar representación inicial si sigue afectando|

Máximo480s agregados,180s por caso, watchdog540s con progreso persistido.
No admitir un caso si coste observado/proyectado más20% no cabe. Estimación
inicial30–100s por caso, no benchmark medido de esta fuente; actualizar tras
el primero. Escritura32MiB, preflight real y reserva2GiB. No reducir precisión.

P1 sólo si, tras P0/temporal, es necesario para distinguir ajuste inicial y
evolución espacial; registrar la decisión antes de admitirlo. Sin más casos.
Si domina temporal176, no atribuir diferencias a espacio ni reducir dt otra
vez automáticamente. Registrar dt/rechazos reales: el CFL puede imponerlos.
Muestras15/30/45/60° sin ajustar los pasos para muestrear.

## Evidencia e interpretación

- Guardar inicial nativo, configuración, receta aceptada/rechazada, fases y
  FAST terminal. El arco parcial no se compacta como ciclo: FAST necesita
  inicial más replay para recuperación, no es checkpoint nativo.
- Observar ambos stages reales: masa, energía, cuatro especies, flujos por
  signo y balances del escape/globales con trabajo/calor/fuentes reales.
  Residuo normalizado1e-12, escalas de inventarios/transportes; no dividir por
  inventarios de especies casi nulas ni modificar criterios del detector.
- Comparar en fases y posiciones comunes presión/densidad/ondas, fracciones,
  frentes, L1/L2/Linf e integrales. Separar diferencia inicial y su crecimiento.
- Etiquetas materiales: intervalo retenido seguro considerando ambas
  inversiones, medias exactas P0/P1 iniciales y cobertura entre mallas. Usar
  intervalo común al comparar; no exigir convergencia puntual en un contacto.
- Trabajo parcial no es trabajo de ciclo ni IMEP periódico. No Richardson/GCI
  forzado. Si no hay contracción, localizar región/fase/interfaz antes de
  corregir. No modificar varios operadores ni extender presupuesto para PASS.

Tres mallas de un arco transitorio no demuestran independencia periódica ni
validación experimental. Cualquier defecto fundamental demostrado detiene
trabajo dependiente y se presenta con evidencia. Sin otras campañas implícitas.
