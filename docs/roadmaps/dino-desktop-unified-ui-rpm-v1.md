# Dino Desktop — navegación unificada y curvas RPM configurables

## Alcance

Rama: `feat/dino-unified-ui-rpm-v1`, basada en el `main` local C05 (`e6c1908`).
Cambio exclusivo de presentación, orquestación y evidencias. No cambia solvers,
ecuaciones, validadores científicos P0–P9 ni contratos de resultados históricos.

- Selector común de familia **2T / 4T nativo / 4T 0D de referencia** dentro de
  `DinoDesktopWindow`; un único menú de proyecto y navegación MODELO / SIMULAR /
  RESULTADOS. El proyecto 4T nativo se abre en la misma ventana y puede guardar
  y recuperar su contexto sin crear otra instancia de aplicación.
- Los contratos de proyecto, solvers y calificaciones científicas permanecen
  deliberadamente distintos por familia. No se convierte ni migra un proyecto
  de un tipo al otro.
- El modo 4T 0D sigue claramente etiquetado `SYNTHETIC_REFERENCE_0D`,
  `NOT_VALIDATED` y **no** se utiliza para calcular potencia/torque nativos.

## Curvas RPM

| Familia | Rango de ejecución/UI | Selección inicial | Algoritmo |
| --- | --- | --- | --- |
| 2T integrado | 2.500–15.000 RPM (contrato público existente) | 2.500–13.000, paso 500 (22 puntos) | Barrido existente con preflight, checkpoints y clasificación por punto |
| 4T nativo | 500–15.000 RPM (guardia **de interfaz**, no dominio científico validado) | 1.000–13.000, paso 500 (25 puntos) | `DINO4T_API_V1`, una corrida por RPM, 30 puntos máx. |
| 4T 0D referencia | 2.500–3.500 RPM, de 2 a 5 puntos (contrato existente) | 2.500–3.500, paso 500 | Referencia sintética, sin extrapolación |

El límite inferior 2T de 2.500 RPM no se reduce a 500 sin ampliar primero
el contrato/verificación del solver; el dominio candidato 2T no constituye
autorización automática para publicarlo.

Para 4T nativo, el formulario exige valores enteros crecientes, extremo
inclusivo exacto, paso positivo y máximo 30 puntos. Cada punto mantiene
su propia configuración, periodicidad, clasificación y manifiesto original.
La curva muestra **únicamente muestras periódicas verificadas**, como
marcadores separados: no conecta puntos ni interpola estados inválidos.

Las simulaciones 4T nativas siguen siendo de ingeniería, no calibradas ni
validadas experimentalmente. En especial, que el preflight acepte 500 o
13.000 RPM no demuestra convergencia, fiabilidad predictiva ni aplicabilidad
física a todo el intervalo.

## Persistencia de 4T nativo

Cada punto se publica mediante `publish_desktop_run` y se vincula al
proyecto nativo mediante su `run_reference` original. La serie se conserva
en `<artifact_root>/dino-4t-native-curves/<project-key>/<series-id>/series.json`,
sin modificar el schema de proyecto C05.

El botón **Abrir curva guardada** verifica proyecto, identidad de
configuración, secuencia RPM, ruta de cada punto y manifiestos originales
antes de graficar. Las cifras del índice por sí solas jamás acreditan
prestaciones: cada muestra graficada debe coincidir con el primario nativo
`VERIFIED` y su enlace geométrico. Alteraciones de identidad o primarios
provocan rechazo o estado `CORRUPT`. Las series siguen separadas de la
historia 4T 0D y de las corridas 2T.

Los trabajos largos tienen cancelación cooperativa y guardan los puntos
ya terminados, sin crear interpolaciones. Requieren configurar la raíz de
resultados de esta máquina en **E:**; un origen en C: queda bloqueado en
este flujo nuevo.

## Verificación y límites

- Tests de navegación en el mismo shell, persistencia 4T nativa, límites
  del barrido, cancelación, no convergencia y apertura fail-closed.
- Regresión 2T/4T focal en Windows Qt offscreen, sin build de distribución.
- Los datos de tests sintéticos no sustituyen corridas del solver real.
- No se prueba aceptación empaquetada Windows ni prestaciones de un motor
  real; no se modifica `main` y no se publica ninguna rama.

## Evidencia de esta implementación

- Regresión conjunta de navegación y Desktop 2T/4T (incluyendo integración
  4T, referencia 4T y curvas): **48 PASS, exit code 0**.
- Tests nuevos de navegación, curva nativa, cancelación y recuperación:
  **10 PASS, exit code 0**.
- Verificación de configuración nativa para **500 y 13.000 RPM: valid=True**
  con el ejemplo 4T. No demuestra periodicidad ni resultados físicos fiables
  a esos regímenes; no se ejecutó el barrido real completo.
- Captura exploratoria Qt offscreen:
  `E:/Dino-artifacts/tmp/dino-unified-4t-preview.png`.
- Durante las primeras pruebas combinadas se detectó `0xC0000409` al
  finalizar pytest. Se aisló la limpieza incompleta de widgets en los tests
  nuevos, se añadió destrucción explícita y la regresión combinada final
  concluyó con **exit 0**.
- No hay build Windows actualizado, ni integración en `main`, ni push.
