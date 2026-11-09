## Context
La auditoría v2 dejó C02/C04 fuera de Etapa 1. F05 todavía redondeaba al aplicar un formulario no editado; F03 aceptaba `initial_state` sin fase; F16 escribía PASS antes de cerrar el proceso; F10 necesitaba una receta explícita; A2-13 no exportaba históricos legacy. El objetivo es cerrar esos bordes sin cambiar ecuaciones ni claims.

## Decisions
### 1. F05 identidad exacta
El editor guarda el valor original por path y sólo re-tipa celdas cuyo texto difiere de la representación cargada. Un Apply sin cambios no llama `replace_engine`. La representación flotante usa `.17g` para round-trip, y los valores no editados conservan el objeto/float original.

### 2. F03 contexto de estado, no state crudo
`run_operating_point` emite `DINO4T_STATE_CONTEXT_V1` con `state`, `theta_deg`,
`model_id` y `complete_cycle`. Sólo acepta un contexto con `complete_cycle=True`;
un state crudo o de medio ciclo devuelve `OPTION_INVALID` antes del solver.
`studies.sweep`/`sensitivity` usan el contexto, no `result["state"]` crudo.

### 3. F16 receipt terminal
El driver Windows escribe `acceptance.json` PASS sólo después de
`process.wait(timeout=15)` y de comprobar `returncode==0`. Un cierre solicitado
no equivale a aceptación.

### 4. F10 receta protegida
`run_protected_regression.py` fija el root de fuente, exige un contexto
histórico explícito y registra el artifact root. La ejecución de esta auditoría:
301 PASS, 3 SKIP, 0 FAIL.

### 5. A2-13 legacy explícito
`export_csv` y el informe incluyen `legacy_loaded` con
`integrity_classification=LEGACY_UNVERIFIED` y `source_qualification`; la
aceptación source reconoce históricos legacy y exporta ambos registros.

## Risks / Trade-offs
- `.17g` puede mostrar más dígitos; preserva identidad exacta y evita un no-op
  silencioso.
- Rechazar state crudo exige que consumidores usen `state_context`; los
  consumidores internos se actualizaron.
- Un histórico legacy exportado sigue siendo `LEGACY_UNVERIFIED`; no se
  promociona a V2.

## Verification
- F05/F03/F16/A2-13 tests en `test_platform_c02_c04_integrity.py`.
- C01/C03, API/A-B/Desktop, Stage2 y receta protegida 301 PASS/3 SKIP.
- Sin build/paquete ni campaña científica.
