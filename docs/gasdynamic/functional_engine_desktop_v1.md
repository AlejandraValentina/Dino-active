# Motor integrado funcional desde Dino Desktop — entrega 1

## Uso

Desde el repositorio: `python -m motorsim.dino_desktop`.
Abrir con Archivo → Abrir el proyecto
`configs/reference_cases/functional_reed_125cc_v1.dino.json`.
En Preparar: seleccionar 9000 RPM, horizonte y presupuesto; elegir artifacts
externos al repositorio. Iniciar corrida y confirmar. Seleccionar la corrida
en el historial y pulsar Ver selección. Los checkpoints permiten reanudar con
la misma identidad de configuración e implementación.

Esta entrega se comprueba sobre la aplicación Python/Qt existente. No se
reconstruye ni se acepta un nuevo EXE: el paquete Windows es la entrega 3.

## Correcciones físicas versionadas

Se activan únicamente al declarar `geometry_identity.gas_exchange_model` con
schema `GAS_EXCHANGE_V2`. La identidad de geometría incorpora todos los valores;
el envelope de configuración conserva también los hashes del código. Sin ese
contrato explícito, las configuraciones antiguas mantienen su comportamiento.

- `intake_control=reed`: conexión geométrica de sección completa, limitada por
  los pétalos cuasiestáticos y el conducto, sin ventana temporal del pistón.
- `intake_control=piston_port`: conserva el control del pistón y rechaza activar
  también pétalos dentro de V2. La admisión híbrida histórica no se reinterpreta.
- `transfer_crankcase_connection=open_duct_face`: sección del conducto hacia
  cárter; apertura geométrica variable sólo hacia cilindro. Se conservan las
  interfaces y donantes de flujo inverso HLLC existentes.
- Barrido: cierre parcial de mezcla/desplazamiento aplicado a la composición
  del flujo que sale del cilindro durante el solape de transfer y escape.
  No es un cociente calculado después de ejecutar.

## Ley de barrido y fundamento

La literatura utiliza desplazamiento, mezcla perfecta y sus combinaciones
como modelos reducidos del barrido: Blair, capítulo 3; Sher, SAE 850085,
<https://doi.org/10.4271/850085>; Assessment of Scavenging Models, SAE 911249,
<https://doi.org/10.4271/911249>.

La ley implementada es una **interpolación local de esos límites**, no una
reproducción del modelo de fases de Benson/Brandham ni una curva medida.

Para inventarios `M_i`, masa total `M` y mezcla declarada `alpha`:

```
y_bulk_i = M_i / M
y_displacement = (0, 0, M_residual / M_spent, M_burned / M_spent)
y_out_i = alpha*y_bulk_i + (1-alpha)*y_displacement_i
```

Sin gases gastados se utiliza `y_bulk`. Antes de aplicar la tasa se limita
cada componente a `M_i/dt` y se redistribuye cualquier demanda restante entre
capacidades donantes disponibles. Así, las tasas son no negativas, su suma
conserva el flujo másico HLLC original y no se consume más inventario del
disponible en la etapa. El cilindro pierde exactamente las especies que recibe
el escape. No hay una fuente artificial ni una corrección posterior de masas.

`alpha=1` representa mezcla perfecta; `alpha=0`, desplazamiento preferente de
gases gastados. El caso de demostración declara **alpha=0.5 como
SYNTHETIC_ASSUMPTION no identificada**; no se ajustó para obtener potencia. Una
recomendación bibliográfica de mezcla de límites no identifica ese parámetro
para este motor ni valida esta interpolación concreta.

La EOS común y la temperatura homogénea del cilindro se conservan; el flujo
energético usa la entalpía donante existente. No se representan temperaturas
separadas de zonas, trayectorias 3D, direcciones de chorros ni generaciones de
carga identificadas individualmente. El modelo reduce la limitación de mezcla
perfecta, pero no demuestra capacidad predictiva sobre geometrías arbitrarias.

Se corrigió además, sólo para el contrato nuevo, el proxy pasivo de fracción
fresca usado por la cámara: cociente de sumas extensivas en vez de suma de
cocientes redondeados. Evita `Y=1.0000000000000002` en mezcla totalmente fresca.
No modifica masas, tolerancias de conservación ni el validador de especies/EOS.

## Integración reutilizada

La ruta es el `run_exploratory` existente, bajo su mismo lock y preflight. Para
el contrato V2 delega en `engineering_workflow`, que utiliza el núcleo del
runner exploratorio ya desarrollado, factorizado en `engineering_point`.
No hay un nuevo sistema de proyectos ni otro runner de barridos.

Se conservan proyectos, variantes, directorios por corrida, historial,
cancelación, callbacks, checkpoints y widgets de resultados. Cada invocación
preserva su configuración, productor y checkpoints en un subdirectorio nuevo.
La reanudación verifica el padre y no repite los ciclos completos.

El formato `DINO_ENGINEERING_RUN_V1` declara balances internos y auditoría
independiente NOT_PERFORMED. Su importador comprueba hashes de resultado,
manifest y muestras; los formatos anteriores conservan su importador auditado.
Los cálculos sin periodicidad muestran estimaciones transitorias en tarjetas
y dejan huecos en curvas definitivas. Presión y flujo pueden visualizarse sin
afirmar potencia periódica. Se muestran sólo los canales realmente guardados,
no un mapa espacial completo inventado.

## Alcance y límites

El caso utiliza 125 cc, 9000 RPM, 44 celdas, CFL 0.4, AFR 11.5 y combustión
existentes. Rigidez 1000 N/m sin experimento de sensibilidad. Fricción explícita
del proyecto: 85000 Pa sintéticos. No hay ajuste de potencia, cambio de
integrador, campaña RPM ni reclamo de validación experimental.

Los preparativos locales cancelados de rigidez 500 N/m permanecen sin stage ni
commit y no forman parte del caso. R2 y los artifacts históricos no se modifican.

La primera entrega demuestra la ejecución e interpretación desde Desktop. La
comparación de dos escapes y su aceptación numérica pertenecen a la entrega 2.
La identificación del barrido, térmica, láminas y pérdidas limita cualquier
reclamo predictivo; resultados transitorios tampoco son una curva estacionaria.
