# Dino 4T — Contrato de integración (`DINO4T_API_V1`)

**Destinatario:** el agente que integre el motor 4T en Dino Desktop y en `motorsim.engine_platform`.
**Estado:** interfaz implementada y probada ([api.py](../../motorsim/dino4t/api.py),
[test_dino4t_api.py](../../tests/test_dino4t_api.py)); **no** hay GUI ni adaptador de plataforma todavía.
**Reclamos:** calibración `NOT_PERFORMED`, validación experimental `NOT_PERFORMED`, capacidad predictiva
`NOT_CLAIMED`. Un resultado 4T es una *simulación con parámetros declarados*, no una medición ni una predicción.

## 1. Regla de dependencia

Desktop y la plataforma dependen **solo** de:

1. las funciones de `motorsim.dino4t.api` (`capabilities`, `validate`, `run`, `check_summary`, `indicator_unit`);
2. los documentos JSON que intercambian: configuración `DINO4T_ENGINE_CONFIG_V1`, resultado
   `DINO4T_OPERATING_POINT_RESULT_V1` y los artefactos de §6.

No deben importar `engine`, `duct`, `restriction`, `twozone`, `equilibrium` ni `runner` (el progreso y las
excepciones internas no son contrato). El núcleo 2T no se toca; el 4T no importa solver 2T (hay un test).

## 2. Puntos de entrada

```python
from motorsim.dino4t import api
api.capabilities()                 # qué ofrece este build (sin cómputo)
api.validate(config)               # {"valid","issues","unknown_keys","config_sha256"}; no lanza
api.run(config, out_dir=None, overrides=None, max_cycles=None, wall_limit_s=3600.0,
        on_progress=None, initial_state=None, allow_unknown_keys=False)   # -> envoltorio
```

Envoltorio de `run`:

```json
{"api": "DINO4T_API_V1", "ok": true, "error": null, "summary": {...}, "artifacts": {...}, "state": "<opaco>"}
```

* `ok` es **verdadero solo si** la corrida terminó **y** es periódica. Una corrida terminada sin periodicidad
  devuelve `ok=false`, `error.code="NOT_PERIODIC"` y el `summary` igualmente adjunto: la GUI puede mostrarlo,
  pero con la advertencia, nunca como resultado.
* `state` es un estado de continuación opaco, válido solo para la **misma topología y malla**; no se serializa
  ni se guarda entre versiones. Si no es compatible, el motor arranca en frío y lo registra en
  `summary.warm_start` (`none` | `used` | `discarded_incompatible_mesh`).
* Ninguna falla esperada lanza excepción. Solo lanzan los errores de programación (`config` que no es `dict`).

## 3. Configuración

* Esquema `DINO4T_ENGINE_CONFIG_V1`. Cada grupo físico lleva `provenance` ∈ `MEASURED`, `DOCUMENTED`,
  `STANDARD_V1`, `SYNTHETIC_ASSUMPTION`, `CALIBRATED`; sin etiqueta se rechaza. **La GUI debe mostrar esa
  etiqueta junto a cada valor** y no debe permitir presentar `SYNTHETIC_ASSUMPTION` como dato de un motor real.
* Selección de modelos (todo en la configuración; **no** hay interruptores globales):
  `combustion.zone_model` ∈ {`single_zone`, `two_zone_equilibrium`}, `numerics.restriction_model` ∈ {`V1`, `V2`},
  `numerics.limiter` ∈ {`minmod`, `van_leer`, `mc`, `unlimited_central`}. Defecto del código: `single_zone` y `V2`;
  el ejemplo usa `two_zone_equilibrium`. **Un modelo ausente no es un modelo elegido**: la GUI debe escribir
  explícitamente las tres claves.
* **Claves desconocidas.** El constructor ignora las claves que no lee; una errata (`restricton_model`)
  seleccionaría en silencio el modelo por defecto. Por eso `validate` informa `unknown_keys` y `run` rechaza con
  `CONFIG_INVALID` salvo `allow_unknown_keys=True`. Límite conocido: la detección compara con el ejemplo y con los
  literales que lee `config.py`; una clave válida colocada en la sección equivocada no se detecta. La GUI debe
  generar la configuración desde un formulario con esquema, no desde texto libre.
* `validate` construye el motor (comprueba mallas y áreas de válvula frente al conducto): `valid` significa
  «ejecutable», **no** «físicamente adecuada».
* `config_sha256` (hash canónico de la configuración resuelta, con `overrides` aplicados) identifica la entrada.

## 4. Resultado

* Claves obligatorias: `api.RESULT_REQUIRED_KEYS`. `check_summary(summary)` devuelve la lista de violaciones y
  además rechaza un resumen que declare validación o capacidad predictiva sin `validation_evidence`.
* Unidades: SI salvo que el sufijo de la clave diga otra cosa (`_bar`, `_kW`, `_Nm`, `_deg`, `_mg`, `_K`, `_J`,
  `_MJ_kg`, `_g_kWh`); `api.indicator_unit(key)` las devuelve. Sin sufijo = adimensional o conteo.
* `final_cycle` contiene los indicadores del **último** ciclo. `cycle_history` resume todos.
* `T_unburned_*`/`T_u` es `NaN` fuera de la zona no quemada: en JSON/CSV debe tratarse como «no definido», nunca 0.
* Los números **no son comparables entre conjuntos de modelos distintos**. `summary.models` declara los modelos
  realmente usados (se deriva de la configuración, no de valores por defecto); cualquier comparación o gráfico que
  mezcle corridas debe verificar que `models` coincida.
* Con `V1` + `single_zone` el resultado reproduce **bit a bit** la etapa 1 (IMEP 12,498382979526601 en el ejemplo).

## 5. Periodicidad y conservación

* `periodicity.status` ∈ {`PERIODIC_CONVERGED`, `NOT_CONVERGED`}; criterios y tolerancias en
  `periodicity.tolerances` (ΔIMEP ≤ 0,2 %, Δm_atrapada ≤ 0,2 %, Δp(θ) ≤ 0,5 %, desbalance de masa ≤ 0,5 %, durante
  2 ciclos). **La periodicidad es una propiedad numérica del modelo, no evidencia de que represente al motor real.**
* `conservation.max_relative_closure` (masa, energía, elementos) debe estar en ~10⁻¹⁴. Que cierre **no** prueba que
  el flujo sea correcto (el defecto D1 de la etapa 1 cerraba a 10⁻¹⁴ con −29 % de caudal): se muestra como control de
  integridad, no como indicador de exactitud.
* `thermo_fit_range_exceeded` y `rejected_steps` se muestran como advertencias de ejecución.

## 6. Artefactos (con `out_dir`)

`summary.json` (el resultado), `config_resolved.json` (entrada exacta tras `overrides`),
`trace_last_cycle.csv` (θ, p, T, V, masa, x_b, quemado, h, q_loss, T_u, T_b, caudales y presiones de lumbrera).
Estos tres archivos son la unidad de persistencia: bastan para reproducir y auditar una corrida
(`config_sha256` + `code_commit` + `code_dirty` + hashes de las fuentes termodinámicas).

## 7. Procedencia

`summary` registra: `config_sha256`, `code_commit`, **`code_dirty`** (si el árbol tenía cambios sin commitear: en
ese caso el commit **no** identifica el código y la corrida no es reproducible por commit), `thermo_sources`
(SHA-256 de GRI-Mech 3.0 y Burcat), `models`, `provenance` por grupo, `evidence_level` (`L1_ENGINEERING_RUN`) y
`claims`. La GUI debe mostrar `code_dirty=true` como advertencia.

## 8. Errores

| `error.code` | Significado | Acción de la GUI |
|---|---|---|
| `CONFIG_INVALID` | Configuración rechazada antes de calcular (incluye claves desconocidas) | Mostrar `detail` (lista de `{code,path,message}`); corregible por el usuario |
| `OPTION_INVALID` | Opción de `run` fuera de rango | Error de programación de quien llama |
| `MODEL_OUT_OF_VALIDITY` | El modelo rechazó un estado que no sabe representar (frontera, termodinámica, paso rechazado 16 veces) | Informar que el punto de operación sale del dominio del modelo; **no** reintentar con más pasos |
| `WALL_LIMIT` | Se alcanzó `wall_limit_s`; resultados parciales | Ofrecer continuar con `state` |
| `NOT_PERIODIC` | Límite de ciclos sin periodicidad | Mostrar con advertencia, nunca como resultado |
| `INTERNAL` | Excepción inesperada | Defecto: guardar entrada y `message` para reporte |

Códigos nuevos pueden agregarse (compatibilidad aditiva): el consumidor debe tratar un código desconocido como
`INTERNAL`.

## 9. Versionado y compatibilidad

* `DINO4T_API_V1`, `DINO4T_ENGINE_CONFIG_V1` y `DINO4T_OPERATING_POINT_RESULT_V1` son **aditivos**: dentro de V1
  pueden aparecer claves nuevas, indicadores nuevos y códigos de error nuevos; **no** se renombra, elimina ni cambia
  de unidad una clave existente. Eso exige una versión nueva (V2) con coexistencia. El consumidor debe **ignorar
  claves desconocidas** del resultado.
* Un cambio de modelo físico que altere números **no** cambia el contrato: se señala con los identificadores de
  `summary.models` y `model_id`. El ejemplo cambió entre la etapa 1 y la 2 (V1→V2, una zona→dos zonas): η_v +1,7 %,
  +4,2 %, +7,5 % a 4000/6000/8000 rpm solo por el contorno. Quien guarde resultados debe guardar `models` y `code_commit`.
* `api.capabilities()` es la fuente para que Desktop descubra modelos seleccionables y códigos; no codificar listas
  en la GUI.

## 10. Ejecución

* Costo medido: ~10 s por ciclo con dx = 20 mm y dos zonas; 4–14 ciclos por punto de RPM (≈ 1–3 min por punto; un
  barrido de 8 RPM ≈ 10 min). **Debe ejecutarse fuera del hilo de la GUI.**
* Un punto por proceso. No se ha verificado el uso concurrente en hilos del mismo proceso; usar procesos.
* No hay cancelación cooperativa: cancelar = terminar el proceso (el resultado parcial se pierde salvo `out_dir`).
  `wall_limit_s` es un límite, no una cancelación.
* `on_progress(dict)` recibe `{"cycle","work_net_J","p_max_bar"}` por ciclo (no un objeto interno).
* Barridos y sensibilidades existen como `studies.sweep` / `studies.sensitivity` y CLI (`sweep`, `sensitivity`), pero
  **no forman parte de `DINO4T_API_V1`**: la entrada para un barrido en Desktop es llamar `api.run` por punto.

## 11. Brechas de `engine_platform.py` (decisiones para quien integre)

`engine_platform` (`ENGINE_PLATFORM_CONTRACT_V1`) fue diseñado antes de esta interfaz. Hoy: registra `4T` apuntando a
`runner.run_operating_point`, devuelve solo el `summary`, comprueba presencia de claves y **propaga excepciones**. No se
modificó (es arquitectura común; el cambio es de quien integre). Recomendaciones, en orden de impacto:

1. **Canal de error único.** Registrar `4T` con `api.run` (no con `runner`) y que la plataforma exponga el
   envoltorio `{ok,error,summary}`; hoy un `CONFIG_INVALID` lanza `ConfigError` y un fallo numérico vuelve como
   `status="failed_numerical"` dentro del resumen: dos canales distintos.
2. **Validación más fuerte.** `engine_platform.check_summary` comprueba claves; debe delegar en
   `api.check_summary` (esquema, estados admitidos, reclamos sin evidencia).
3. **Indicadores comunes.** Los nombres del 4T (`volumetric_efficiency_intake_valve`, `trapped_mass_mg`) no equivalen
   a magnitudes 2T (relación de entrega, atrapamiento por barrido). Definir un subconjunto común explícito
   (`imep_net_bar`, `brake_power_kW`, `brake_torque_Nm`, `bsfc_g_kWh`, `p_max_bar`, `T_max_K`, `trapped_mass_mg`) y
   **no** comparar el resto entre familias sin definición común.
4. **Opciones.** Unificar nombres (`on_progress` frente a `progress`, `wall_limit_s`) y excluir `initial_state` del
   contrato de plataforma (es específico de familia).
5. **Adaptador 2T.** Sigue sin registrarse a propósito: requiere su propio adaptador revisado que no altere
   contratos congelados. El 4T no depende de ello.
6. **Descubrimiento.** Añadir `capabilities(cycle)` a la plataforma delegando en `api.capabilities`.

## 12. Riesgos pendientes para la integración

| Riesgo | Efecto | Mitigación |
|---|---|---|
| Parámetros sintéticos presentados como de un motor real | Conclusión de ingeniería sin base | Mostrar `provenance` y `claims` siempre; bloquear etiquetas `MEASURED`/`CALIBRATED` sin referencia |
| Comparar corridas con modelos distintos | Diferencias de hasta 8 % que no son de diseño | Exigir igualdad de `summary.models` |
| Interpretar `ok=true` o periodicidad como validez | Falsa confianza | Texto fijo de alcance junto a todo resultado |
| Puntos de operación fuera del dominio (p. ej. soplado muy intenso) | `MODEL_OUT_OF_VALIDITY` | Tratarlo como resultado informativo, no como fallo de la GUI |
| Hilos/GUI bloqueada por ~minutos por punto | Mala experiencia | Proceso externo + `wall_limit_s` |
| `code_dirty=true` | Resultados no reproducibles por commit | Advertencia visible |
| Sin `INDEPENDENT_REVIEW` | Revisión solo propia | No hacer afirmaciones externas |

## 13. Lista de comprobación para el integrador

1. Llamar `api.capabilities()` al iniciar y construir selectores de modelo desde ahí.
2. Generar configuración desde formulario; escribir explícitos `zone_model`, `restriction_model`, `limiter`.
3. `validate` antes de `run`; mostrar `issues` y `unknown_keys`.
4. Ejecutar `run` en un proceso separado, con `out_dir` único por corrida.
5. Persistir los tres artefactos de §6; indexar por `config_sha256` + `models` + `code_commit`.
6. Mostrar siempre: `claims`, `provenance`, `periodicity.status`, `code_dirty`, cierre de conservación.
7. Ejecutar `tests/test_dino4t_api.py` en CI del integrador; si falla, el contrato cambió.
