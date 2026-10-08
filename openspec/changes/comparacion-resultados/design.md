## Alcance
Vista accesible desde Simulación 2T; dos resultados independientes del editor.
`load_result` sigue siendo el único lector. No se inicia QProcess al seleccionar,
comparar o exportar. Resultados inválidos no sustituyen la selección anterior.

## Compatibilidad y datos
Comprobar convergencia/balances y comparar campos explícitos de modelo/configuración
admitida, régimen, gas, contornos, Cd, aporte, referencia angular, receta inicial
p/T/Y, perfil y variante. Metadata ausente impide acreditar compatibilidad y se
identifica. No comparar literalidad de archivos, geometría, m/U/F derivados ni
identidades/nombres/rutas/dirty como condiciones de funcionamiento.
Reutilizar `validated_model` para interpretar geometría canonizada por función.
Resumen por campos de ficha, cárter, lumbreras, falda y tramos; nombres y descripción
separados. Igualdad numérica considera 54 y 54.0 equivalentes; filas de lumbreras
se canonizan por geometría/función, sin confundir orden de presentación con motor.

Tabla del último ciclo convergido validado: W_C, W_K, pmax, Y_I/K/C/E; B−A.
Porcentaje solo trabajos/presión: 100*(B−A)/abs(A), no definido con A=0.
No recalcular trabajo o máximo desde muestras. Gráficas con ejes comunes para
A sólida azul y B discontinua naranja; presión kPa absolutos y volumen cm³.
Ángulo alineado restando 360*(número de ciclo−1), conservando 180–540° y todos los
puntos en orden temporal, incluido P-V. Sin desplazar picos, suavizar ni inventar datos.

## CSV
UTF-8 sin BOM, coma, punto decimal, `csv.writer` con escape de comillas estándar.
Carpeta nueva exclusiva; errores eliminan únicamente archivos propios incompletos
si es posible, nunca anuncian éxito parcial ni modifican fuentes.
`resumen.csv`: magnitude, unit, run_id_A, run_id_B, value_A, value_B, difference_B_minus_A,
relative_difference_percent. Vacío para porcentaje no definido o no aplicable a Y.
`curvas.csv`: configuration, run_id, sample_index, angle_cycle_deg, angle_original_deg,
pressure_absolute_Pa, volume_m3. Formato largo, primero A luego B, puntos originales
sin redondear. No se persiste sesión de comparación ni modifica JSON v5.

## Comprobación y parada
Usar resultados existentes editor-20260915/A y B (ambos perfil B); C sirve únicamente
para probar rechazo de perfil distinto. Unit tests con esperados independientes,
fixtures identificados si se necesitan; ninguna ejecución nueva. Windows visible
al 150 % con captura y CSV reales, separado de aceptación manual. Una revisión
puntual; registro en README/tasks/hoja. Entrega 6 En curso, pendientes barridos e
importación experimental, sin desarrollar esos alcances ni iniciar entrega 7.


## Ampliación autorizada: punto y barrido RPM
La prohibición anterior de nuevos cálculos pertenece al primer tramo A/B.
Ahora solo RPM varía: entero 2500–3500, punto inicial 3000; inicio/final/paso
producen 2–5 puntos ascendentes, exactos, paso positivo, lista previa visible
(inicial 2500/3000/3500). Límites de producto, no certificado de dominio físico.
ProjectCase especializado parametriza rpm sin modificar SyntheticCase ni ecuaciones.
Model.rate=6*rpm gobierna dV/dt, energía/marcador temporal y dt; muestras usan
(angle-initial_angle)/(6*rpm). Aporte angular 350°/40° intacto, vuelta 60/rpm s.

Un QProcess existente ejecuta la serie secuencialmente. Una copia JSON independiente
incluye geometría/dirty/origen y lista; cada execute reconstruye modelo e inventarios
originales, sin warm-start. Fallo/no convergencia/cancelación detienen y conservan
prefijo/diagnóstico, restantes no ejecutados. 30 ciclos/60 s por punto, hasta 300 s
acumulados; presupuestos de memoria/RHS/pasos/rechazos/dominio intactos. Inicio,
escritura, integración y total de cada punto separados en el índice; total de
serie incluye validación/escrituras, tiempo percibido de interfaz incluye proceso.

### Contrato de resultados v3 y serie v1
V1 referencia y v2 proyecto mantienen lectura/reconstrucción fija 3000. V3 añade
operating_point={rpm:int} y escenario S2T-0D-reference-recipe-variable-rpm-v1;
reconstrucción estricta de todo el escenario, no parámetros arbitrarios del archivo.
Para puntos de serie, series_context={series_id:32 hex,point_index:0..4} forma parte
de entradas validadas. Mismos tres archivos con hashes/manifiesto y unidades;
coherencia tiempo/ángulo se valida con RPM efectivas. A/B admite contratos viejos
compatibles a 3000 e impide diferente RPM/perfil. JSON de proyectos v5 no cambia.

series.json (motorsim-rpm-sweep, version 1) guarda series_id, common_inputs, rpms,
points, state, reason, integration_seconds y wall_seconds; interfaz añade
interface_wall_seconds tras terminar. Cada punto guarda rpm/state/reason,
result (point-NN/manifest.json o null), run_id, manifest_sha256 y timings separados.
Carpeta exclusiva, índice actualizado atómicamente por punto y al terminar.
Lector exige prefijo secuencial, estado/identidad/hash/entradas comunes/posición
coincidentes y rutas internas exactas, incluyendo resolución de enlaces. Reabrir
no usa proyecto ni ejecuta. El aviso de configuración anterior conserva procedencia.

Tabla RPM/estado/ciclos/segundos/W_C/W_K/pmax, causa visible al seleccionar fila.
Magnitudes aceptadas vacías salvo convergencia. Consultar punto reutiliza vista
individual. Dos gráficos de puntos sin uniones/ajuste/extrapolación: W_C y pmax
frente RPM, sin potencia/par/óptimos. CSV serie.csv reutiliza escritor exclusivo;
columnas con unidades, ids, estados y motivos incluso no ejecutados. A/B intacto.

### Comprobación de este tramo
Tests focalizados de contrato/control con dobles explícitos, sin evidencia física
fabricada. Solo barrido GUI B 2500/3000/3500 geometría exacta de referencia 8:1;
3000 debe reproducir referencia. Si todos convergen/controlan, dos C extremos.
Contraste B/C con umbrales existentes (incluye Y y masas), sin afirmar tendencia.
Windows 150 % visible/captura separado de aceptación manual; una revisión puntual.
Entrega 6 En curso, importación experimental y entrega 7 fuera del alcance.


El manifiesto v3 producido por execute registra timings con setup_seconds,
writing_seconds (datos/hashes/manifiesto inicial), integration_seconds y wall_seconds
hasta ese registro. El cierre del registro de tiempos se incluye en el total de
serie y de interfaz. En puntos GUI, interface_wall_seconds se añade tras finalizar;
en consola el total corresponde al proceso numérico. Un diagnóstico construido
sin ejecutar puede carecer de tiempos; el lector no los inventa. El índice de
serie conserva los tiempos del punto; nunca modifica manifiestos hijos.
La interfaz exige destino inexistente y el identificador sweep_started confirmado
por el hijo antes de actualizar el índice: un fallo no puede apropiarse de otra serie.


## Datos externos: ampliación autorizada del 16/09/2026
El tramo anterior conserva su evidencia. Ahora se permite importar sin cálculos
nuevos, física, ampliación de RPM, calibración ni JSON v5. Dos módulos pequeños:
external_data (CSV/contrato/aritmética) y external_view (declaración/consulta Qt).
Acceso Datos externos junto a comparación/barrido. No lee el editor ni inicia procesos.

CSV de una curva: UTF-8 con BOM opcional, encabezado exacto rpm,value, coma y punto
decimal, sin miles ni expresiones. Al menos una fila, exactamente dos columnas,
RPM positivas finitas sin duplicados numéricos. Trabajo admite negativo/cero;
presión absoluta positiva. Validación completa con fila/columna, sin omitir filas.
Se permite notación científica decimal y espacios exteriores en valores, nunca
inferir delimitador/unidad por nombre. Límites de archivo 16 MiB/100000 filas y
80 caracteres por número, representable finito sin desbordamiento/subdesbordamiento
a cero. RPM externas no están restringidas a 2500–3500. Decimal conserva identidad
exacta de RPM, incluso cuando convertir a float las haría coincidir; copia ordenada
para consulta, CSV original sin cambios. Conversión bar*100000 con valores originales.

Magnitud/unidad y definición deben declararse antes de vista previa. Trabajo:
integral p dV de 360°, un cilindro 2T, intercambio de gases incluido, sin descontar
cárter/pérdidas mecánicas. Presión: máximo absoluto del cilindro, no manométrico ni
potencia. No se aceptan trabajo parcial ni potencia/par al eje ni conversiones de
freno a indicado. Ayuda contextual y confirmación explícita de definición completa.
Procedencia inicial No determinada; otras: Medición declarada, Simulación externa,
Ejemplo sintético. Medición es declaración, no prueba de autenticidad/metrología.
Nombre/fuente/motor/configuración/condiciones/observaciones pueden ser No informado.
Nunca copiar condiciones del solver hacia estos campos.

Vista previa no sustituye la selección confirmada. Modificar declaraciones invalida
vista previa/confirmación. Cancelar archivo/declaración/destino no cambia selección.
Confirmar exige carpeta nueva y guarda bytes CSV en original.csv y metadata.json
al final, formato motorsim-external-rpm versión 1, dataset_id UUID hex, metadata,
rules exactas y csv_sha256. Lector revalida reglas/definición/unidades/identidad,
ruta interna fija/hash y vuelve a analizar CSV. No requiere origen. Utiliza
write_json existente en carpeta exclusiva, limpieza solo de archivos propios ante
fallo; no éxito parcial. No catálogo ni modificación de manifiestos del barrido.

load_sweep valida barrido independiente del editor. Contraste une RPM exactamente
iguales, sin redondeo/interpolación/extrapolación. Valor simulado procede del resumen
W_C_J o p_max_Pa del último ciclo convergido. Diferencia simulado−externo; relativa
100*diferencia/abs(externo), ausente con base cero. Unión de RPM conserva externos
sin pareja y puntos simulados no convergidos/no ejecutados, magnitudes ausentes
vacías. Se muestran estado y causa. Protecciones A/B sin cambios; este modo distinto
no exige perfiles numéricos ni parámetros sintéticos al dato externo.

Siempre se identifica contraste descriptivo y Equivalencia de condiciones no
acreditada: metadatos completos tampoco certifican equivalencia. Detalles muestran
ambas procedencias/identidades, geometría y condiciones guardadas del barrido.
Tabla canónica y puntos sin líneas (no se atraviesan fallos): cuadrados azules
simulados, círculos naranjas externos con leyenda de procedencia; huecos si no se
calculan diferencias. No filtros favorables, máximos ajustados ni umbrales experimentales.

contraste.csv usa write_csv_files existente, carpeta exclusiva, UTF-8/coma/punto.
Incluye RPM/magnitud/unidad, externo/simulado/diferencia/relativa/estado, dataset_id,
procedencia/fuente, series_id/run_id, unidad/valor originales, motor/configuración/
condiciones/definición/aviso/motivo. Ausencias vacías. Ninguna procedencia sintética
se renombra Medición; no se modifican las fuentes. Pruebas numéricas independientes
sin solver y recorrido Windows 150 % con barrido existente y CSV sintético rotulado.
