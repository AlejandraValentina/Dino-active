# C05 — plan reproducible de integración controlada

Fecha: 2026-11-09. Rama: `fix/dino-platform-c05-prep-v1`.
Alcance: preparación de fuente y evidencia. **No** se ejecuta merge, push,
build ni campaña científica.

## 1. Secuencia verificada

Comandos de verificación (sólo lectura):

```text
git merge-base main HEAD
git merge-base --is-ancestor work/dino4t-ab-engineering-v1 HEAD
git log --oneline --graph --decorate main..HEAD
```

Resultado: `main` (`5e4ba4d`) es ancestro de `HEAD`; la rama A/B (`8b371e2`) y
la auditoría (`353e3f0`) también. La integración propuesta es
**fast-forward**, conserva todas las historias y no requiere merge con
conflictos.

| Orden | Revisión | Contenido |
|---|---|---|
| 1 | `5e4ba4d` | `main` oficial |
| 2 | `8b371e2` | A/B estricto, cancelación cooperativa, exportaciones |
| 3 | `353e3f0` | auditoría y replanificación unificada 2T+4T |
| 4 | `05b7a82` | correcciones P1 |
| 5 | `2fc8d70` | C01/C03 |
| 6 | `fa81e9c` | C02/C04 |
| 7 | `668b20b`, `fd43f73`, `d1fbce7` | base previa de la rama C05: 4T 0D, curva RPM y documentación |
| 8 | `f93714b`, `edba678`, `fb48277`, `0b9e137`, `8be8196`, `ffc89b3`, `b92b744` | C05 prep: F03/F15/F16/A2-03 en fuente y correcciones de la revisión independiente |

Rango de preparación verificado: `668b20b..bd33c78`. Los commits de registro,
logs y de este documento son posteriores y no cambian código de producto. La ascendencia se verifica con
`git merge-base --is-ancestor main HEAD`; no hay commits de merge.

## 2. Incompatibilidades residuales

| Tema | Estado | Evidencia / criterio |
|---|---|---|
| F03 reanudación | Cerrado en fuente | `tests/test_platform_c05_resume.py`; medio ciclo/fase/modelo/topología rechazados; `continuation` vs `warm_start`; reinicio exacto no declarado |
| F15 workers Qt | Cerrado en fuente | `tests/test_platform_c05_qt_lifecycle.py`; reserva única, cierre durante ejecución, sin huérfanos, `QRunnable` con token |
| F16 aceptación | Cerrado en fuente | `tests/test_platform_c05_terminal_acceptance.py`; PASS sólo tras wait/exit code/recursos; error/timeout/incompleto retenidos |
| A2-03 curva 4T 0D | Cerrado en fuente | `tests/test_four_stroke_curve_reference.py`, `test_desktop_four_stroke_curve_binding.py`; identidad, persistencia, reapertura, parcial/obsoleta/corrupta; separado del 4T nativo |
| Aceptación Windows | **PENDIENTE** | Requiere build autorizado y candidato nuevo; el paquete A/B previo no prueba estos cambios |
| `test_cae_ui.py` | Justificado | El dominio 2T llega a 15001 rpm y el artefacto externo ausente se declara `skip`; no se convierte un fallo en PASS |
| Packaging | Sin cambio de datos nuevos | Los módulos nuevos viven bajo `motorsim/`; `packaging/bundle_inputs.py` sigue siendo la autoridad de insumos consumidos |
| Programa/AGENTS | Actualizado | `program-status.json` y el bloque `CURRENT_OBJECTIVE` apuntan a `DINO_PLATFORM_C05_INTEGRATION_PREP_V1` |

## 3. Criterios de aceptación verificables

### Fuente

```text
python -m pytest tests/test_platform_c05_resume.py \
  tests/test_platform_c05_qt_lifecycle.py \
  tests/test_platform_c05_terminal_acceptance.py \
  tests/test_four_stroke_curve_reference.py \
  tests/test_desktop_four_stroke_curve_binding.py \
  tests/test_desktop_four_stroke_curve_page.py \
  tests/test_platform_c02_c04_integrity.py \
  tests/test_c01_c03_native_contracts.py \
  tests/test_platform_p1_incompatibilities.py \
  tests/test_dino4t_api.py tests/test_dino4t_ab_comparison.py \
  tests/test_dino4t_desktop_integration.py -q
```

### Contratos protegidos

- P9 SHA-256:
  `79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d`.
- `git diff` sin cambios en P0–P9, ecuaciones, tolerancias, expected values ni
  evidencia histórica.
- Receta protegida F10, sólo si el contexto histórico está disponible:
  `DINO_ARTIFACT_ROOT=E:/Dino-artifacts python -u results/platform-c01-c03-remediation-v1/verification/run_protected_regression.py E:/dino/Dino-active`.

### Evidencia registrada

- `results/platform-c05-integration-prep-v1/verification/c05-focused-final2.summary.json`
  → **249 passed, 1 skipped**, exit 0.
- `results/platform-c05-integration-prep-v1/verification/c05-protected-final.summary.json`
  → **301 passed, 3 skipped**, exit 0.
- `results/platform-c05-integration-prep-v1/reviews/independent-c05-review.md`
  → **APPROVE** a nivel fuente; hallazgos Altos resueltos; riesgos residuales
  Bajos documentados.
- `openspec validate platform-c05-integration-prep-v1 --strict` → válido.

### Integración

```text
git merge-base --is-ancestor main HEAD   # exit 0
git rev-list --count main..HEAD          # commits preservados
```

No se ejecuta `git merge`, `git push` ni build.

## 4. Distinción de estado

- **Aceptado a nivel fuente:** F03/F15/F16/A2-03 con contratos y tests propios.
- **Verificado en ejecución local:** suites focalizadas, servidores falsos de
  proceso/hilo y reapertura de proyectos; no es validación física.
- **Pendiente para aceptación Windows completa:** build, paquete, UIA y
  verificación de recursos en un candidato nuevo. Sin ese candidato, C05 no se
  declara integrado en `main`.
- **Sin claim científico:** calibración `NOT_PERFORMED`, validación
  experimental `NOT_PERFORMED`, predictiva `NOT_CLAIMED`.


## 5. Cierre de esta etapa

- Gate `DINO_PLATFORM_C05_INTEGRATION_PREP_V1`: **PASS** con clasificación
  `C05_SOURCE_PREP_COMPLETE_WINDOWS_ACCEPTANCE_PENDING`.
- `C05-WINDOWS-ACCEPTANCE`: `BLOCKED_LOCAL`, porque no existe autorización de
  build/candidato para el código posterior a C05.
- Este cierre es de preparación y fuente; no declara C05 integrado en `main`
  ni aceptado en Windows.
