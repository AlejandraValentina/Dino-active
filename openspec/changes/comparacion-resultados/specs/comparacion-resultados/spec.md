## ADDED Requirements

### Requirement: Dos resultados validados independientes del editor
MUST ofrecer Comparar resultados desde Simulación 2T, A/base y B/modificada, mediante
el lector existente de manifest.json. MUST mostrar identidad del proyecto/run_id,
origen, régimen, modelo, variante, perfil y convergencia. MUST conservar selección
anterior ante archivo ilegible. MUST NOT calcular, usar o modificar el proyecto activo.

#### Scenario: Archivo inválido
- **WHEN** se intenta reemplazar A o B con un resultado ilegible
- **THEN** se explica el error y se conservan selección y datos anteriores.

### Requirement: Compatibilidad y diferencias explícitas
MUST exigir convergencia y balances, modelo/configuración física, condiciones
(rpm, gas, contornos, Cd, energía, receta p/T/Y y referencias), perfil y variante
iguales. MUST explicar diferencias o metadata faltante sin comparación cuantitativa.
MUST permitir geometría/m/U/F derivados y metadata/origen distintos. MUST resumir
todas las diferencias geométricas de ficha, cárter, lumbreras, falda y conductos,
separando cambios descriptivos; números equivalentes y orden de filas equivalentes
de lumbreras MUST NOT considerarse cambios físicos. MUST reutilizar correspondencia por función.

#### Scenario: Perfil distinto o diagnóstico
- **WHEN** uno de los resultados tiene otro perfil o no está convergido con balances aprobados
- **THEN** se identifica su estado y la causa que impide comparar/exportar, sin curvas cuantitativas vigentes.

### Requirement: Tabla y superposición fieles
MUST mostrar A, B, B−A de trabajos C/K separados, pmax y Y de los cuatro volúmenes
desde resumen validado. Porcentaje de trabajo/presión MUST ser 100*(B−A)/abs(A),
no definido con A=0; Y solo diferencia absoluta. MUST superponer muestras con
estilos A/B distinguibles, ejes comunes, presión absoluta y unidades. Alineación
MUST restar vueltas completas según referencia de cigüeñal, sin alinear picos ni
ordenar P-V por volumen. MUST NOT suavizar/inventar datos ni declarar motor mejor,
potencia al eje o validez experimental. MUST mantener aviso 0D/energía prescrita/sin ondas.

#### Scenario: Diferentes ciclos de convergencia
- **WHEN** A y B convergieron en distinto número de vueltas
- **THEN** se comparan sus últimas vueltas por la misma fase, preservando muestras originales y orden temporal.

### Requirement: Exportar comparación compatible sin sobrescribir
MUST exportar resumen.csv y curvas.csv a carpeta nueva, UTF-8/coma/punto decimal,
escape correcto, valores sin redondear, unidades e identidades A/B y run_id en ambos.
Curvas MUST incluir ángulo de ciclo, presión absoluta y volumen. MUST informar
fallos sin éxito parcial ni modificar resultados fuente o archivos existentes.

#### Scenario: Escritura fallida o destino existente
- **WHEN** no pueden escribirse los dos CSV o ya existe el destino
- **THEN** se informa el error, se conserva la comparación cargada y no se sobrescriben archivos.


### Requirement: Régimen acotado y lista exacta
En proyecto actual MUST admitir punto RPM entero 2500–3500 inicial 3000, o barrido
2–5 enteros distintos ascendentes del mismo rango, paso positivo y extremo exacto.
MUST mostrar lista antes de ejecutar (inicial 2500/3000/3500) y rechazar inválidos
sin sustituciones. Referencia MUST permanecer 3000; condiciones, perfil B/100 Pa,
leyes y criterios MUST conservarse; JSON v5 MUST NOT cambiar.

#### Scenario: Plan inválido
- **WHEN** se ingresa tipo/rango/paso/cantidad o extremo incompatible
- **THEN** se explica el error y no se inicia cálculo ni se ajusta silenciosamente.

### Requirement: Parametrización y secuencia independiente
MUST propagar RPM a grados/segundos (6*rpm), vuelta (60/rpm), dV/dt, tasas de energía
y marcador, muestras y validación. Aporte angular 350°/40° MUST conservarse.
MUST capturar una única geometría válida incluso sin guardar y lista independiente.
Un solo cálculo activo MUST ejecutar puntos secuenciales desde receta inicial,
sin estado heredado. MUST mostrar punto/total/rpm/ciclos/tiempos reales. Cada punto
MUST respetar 30 ciclos/60 s y límites vigentes; serie máximo 300 s integración.
MUST registrar inicio/escritura separados y total percibido. Cancelar/fallar/no
converger MUST detener sin reintentos, conservar diagnóstico/prefijo y marcar
restantes no ejecutados. Cierre MUST proteger edición y evitar huérfanos.

#### Scenario: Edición y fallo intermedio
- **WHEN** se edita el motor tras iniciar y el segundo punto falla
- **THEN** se conserva la copia inicial para toda la serie, resultado anterior/diagnóstico y restantes sin ejecutar.

### Requirement: Serie persistente y resultados compatibles
MUST guardar resultados individuales v3 reconstruidos estrictamente con RPM,
conservar lectores v1/v2 a 3000 y comprobar tiempo–ángulo efectivo. MUST registrar
índice local con identidad/copia/lista/estados/resultados/motivo, actualizado por
punto/final, sin sobrescrituras. Reabrir MUST validar identidades/entradas/posición,
rechazar rutas externas y cruces de series, no requerir proyecto ni recalcular.
MUST conservar aviso de configuración anterior. A/B MUST admitir versiones
compatibles a igual condición efectiva y rechazar diferentes RPM/perfiles.

#### Scenario: Índice ajeno
- **WHEN** un índice apunta a un punto de otra serie o a una ruta externa
- **THEN** se rechaza y se conserva la selección anterior.

### Requirement: Consulta y CSV del barrido
MUST mostrar RPM/estado/ciclos/tiempo/W_C/W_K/pmax y causas; fallidos/no ejecutados
MUST tener magnitudes aceptadas vacías. Punto convergido MUST abrir vista individual.
MUST dibujar puntos reales W_C/RPM y pmax/RPM sin ajuste, extrapolación ni unión
sobre fallos. MUST mantener aviso 0D prescrito/sin ondas ni sintonía y MUST NOT
mostrar potencia, par u óptimos. CSV MUST conservar unidades/ids/estados, incluidos
no ejecutados, reutilizando exportación exclusiva sin alterar CSV A/B.

#### Scenario: Serie interrumpida
- **WHEN** se reabre y exporta una serie con punto no convergido
- **THEN** se muestran/exportan causa y estado sin ceros como magnitudes aceptadas, ni curvas inventadas.


### Requirement: CSV externo explícito y validación completa
MUST importar una curva UTF-8/BOM opcional, coma, punto decimal, dos columnas
rpm,value y al menos una fila. RPM MUST ser positivas finitas y únicas, sin
restricción 2500–3500; valores MUST ser finitos. MUST exigir magnitud/unidad y
definición: W_C J/ciclo de un cilindro 2T integral p dV de 360° con intercambio de
gases sin descontar cárter/pérdidas, o pmax absoluta Pa/bar (factor 100000).
Trabajo MUST admitir signo/cero; presión MUST ser positiva. MUST NOT admitir
manométrica, potencia/par al eje, trabajo parcial, otras unidades o inferencias.
MUST conservar originales y ordenar solo copia. Error MUST indicar fila/columna
y rechazar todo sin sustituir selección válida, sin eliminar/mediar/rellenar filas.

#### Scenario: RPM casi iguales o duplicadas
- **WHEN** el CSV tiene RPM duplicadas o distintas más allá de la precisión binaria
- **THEN** se rechazan duplicados numéricos y se preserva la distinción decimal exacta de los demás, sin forzar coincidencias.

### Requirement: Procedencia, revisión y persistencia de importación
MUST ofrecer nombre, procedencia inicial No determinada (también Medición declarada,
Simulación externa, Ejemplo sintético), fuente, motor/configuración, condiciones y
observaciones con No informado permitido. MUST NOT inventar ni copiar condiciones
sintéticas como ensayo. Medición declarada MUST identificarse como declaración sin
autenticación/metrología. Flujo MUST seleccionar CSV, declarar, revisar, confirmar;
cancelación MUST preservar selección. Confirmación MUST guardar carpeta nueva con
CSV original y metadatos/identificador/reglas/unidades/procedencia; reapertura MUST
validar correspondencia/estructura/metadatos sin requerir CSV fuente. MUST NOT
sobrescribir ni anunciar éxito ante fallo; originales, proyectos y barridos intactos.

#### Scenario: Cancelación y origen ausente
- **WHEN** se cancela una nueva importación o se reabre una confirmada sin su CSV fuente
- **THEN** la cancelación conserva el conjunto anterior y la reapertura utiliza y valida su copia local.

### Requirement: Contraste descriptivo por coincidencia exacta
MUST usar load_sweep sin proyecto actual ni cálculo. MUST mostrar ambas identidades,
procedencias, geometría/condiciones guardadas, magnitud/unidades, puntos disponibles
y coincidentes. Solo RPM exactas con simulación convergida MUST generar diferencias
simulado−externo y 100*diferencia/abs(externo), relativa indefinida con externo cero.
MUST usar W_C/pmax del resumen validado y conservar estados/no parejas sin ceros
inventados. MUST NOT habilitar diferencias con definición incompatible, interpolar,
redondear RPM, extrapolar, completar simulando ni cambiar gate A/B. MUST identificar
contraste descriptivo y Equivalencia de condiciones no acreditada ante información
faltante; MUST NOT certificar validación/calibración ni adoptar tolerancias del solver
como umbrales experimentales ni exigir sus parámetros a datos externos.

#### Scenario: Punto fallido y base cero
- **WHEN** un punto del barrido no converge o una base externa coincidente vale cero
- **THEN** se conserva el diagnóstico sin resultado simulado aceptado y la relativa a cero queda sin definir.

### Requirement: Consulta gráfica y exportación externas sin motor
MUST ofrecer Datos externos, formulario compacto/ayuda, tabla y gráfico por RPM,
con distinción simulado/procedencia externa y externos sin pareja. MUST dibujar
solo datos cargados sin líneas a través de fallos, ajuste/suavizado ni búsqueda de
coincidencias favorables. CSV MUST incluir RPM/magnitud/unidad canónica/valores/
diferencias/relativa/estados y referencias con procedencia, en carpeta nueva.
Importar/consultar/exportar MUST NOT cambiar proyecto/dirty/resultados ni iniciar
QProcess. Pruebas MUST usar CSV claramente sintético y barrido real existente,
sin sustituirlo por convergencia fabricada ni nuevas ejecuciones.

#### Scenario: Ejemplo sintético exportado
- **WHEN** se contrasta y exporta un CSV de ejemplo sintético
- **THEN** vista y exportación conservan esa procedencia sin presentarlo como medición o validación experimental.
