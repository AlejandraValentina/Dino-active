# Revisión adversarial R3 de P4→P8 — 2026-09-29

**Dictamen: `INDEPENDENT_REVIEW_BLOCKED_MATERIAL_FINDING`.** No se otorga `INDEPENDENT_REVIEW_PASS`; P4–P8 no quedan ratificados por R3 y P9 sigue detenido. P4 conserva su clasificación científica previa (`P4_FINAL_BLOCKED_C3_INCONCLUSIVE` en la decisión humana de governance); el `P4_PASS` técnico que registra la matriz queda sin ratificar. La validación experimental permanece `NOT_PERFORMED`.

## Baseline, alcance y método

Revisé `main` en HEAD `ca859e04043e027240815a2acd778784deae400f`; `origin/main` estaba en `d616e2946d84080be44e21867602855d12f7c54a`, ocho commits detrás. El árbol estaba limpio. `git diff --check` y `git lfs fsck` pasaron. No hice fetch, push, reset ni rebase. El delta R2 examinado fue `4214703..ca859e0`; no cambió código en `motorsim/` desde la campaña P8 `437a66f`.

Declaro la limitación de independencia: este mismo agente implementó la remediación R2 en el hilo anterior. Para reducir ese sesgo, dos agentes de solo lectura sin contexto previo revisaron C3/P4 y P5–P8. El segundo reprodujo el hallazgo P8; el primero verificó partes de C3, pero agotó su cuota antes de terminar el vínculo runtime. Por tanto, este dictamen no se presenta como una revisión personal plenamente independiente. Los impedimentos técnicos concretos siguientes bastan para bloquear cualquier ratificación.

## R2 y auditoría G2-v2

Repetí en una copia temporal la mutación R2 del checkpoint 50: cambié `inputs.gate_inputs.segments[0].stages[0].dt` de `1.0723312057482394e-06` a JSON `false` y actualicé `decision.closing_checkpoint_sha256`. El auditor devolvió `E13_G2_V2_INCONCLUSIVE`, razón `MALFORMED_CFL_DT`; no reproduje el MAJOR R2. La copia temporal se eliminó. El código exige `type(value) in (int, float)`, finitud y positividad en `dt` y límites. Las pruebas `tests/test_p4_g2_v2_recovery.py`, `tests/test_p4_c3_r5_audit.py` y `tests/test_periodicity_e13_r1.py` pasaron: **82 passed**.

Recalculé desde los checkpoints y sus historias las comparaciones decisivas con un script de análisis separado, sin llamar al comparador de producto. 44 vs 42: `sensor_max=0.00618179998843072`, FAIL; 48 vs 46: `0.0005056779434901066`, PASS; 50 vs 48: `0.000508629756519752`, PASS. El auditor R2, ejecutado sobre la evidencia completa, clasifica `E13_G2_V2_PASS`, periodo 2, ciclo 50, streaks A=15/B=3.

### BLOCKER R3-001 — conservación G2 31–50 no es reauditable desde evidencia primaria

La preregistración exige conservar inventarios/ledger y evidencia completa por ciclo para auditar conservación. Sin embargo, los checkpoints 31–50 solo guardan `state`, `cells`, `history`, `work_indicated_J`, `port_integral`, `initial_cylinder_mass` y `gate_inputs`. El gate contiene `global_balance` y `physical_balance` ya calculados, además de residuos y etapas, pero no `initial_inventory`, `final_inventory` ni `external`. La muestra de historia guarda ángulos, presión de cilindro y sensores; no guarda intercambios externos. Confirmé la estructura en `checkpoint_cycle050.json.gz` y en checkpoints 31 y 30.

El productor `motorsim/hybrid_fast.py` calcula el balance global con inventario inicial, inventario final y flujos externos; el agregador `dev_orchestrator/p4_g2_v2_recovery.py` reduce esos registros a residuos precomputados. El auditor offline los valida por tipo y límite, pero no puede recomputar el balance desde sus términos físicos. El valor persistido pequeño no demuestra por sí mismo que estén incluidos todos los intercambios o el control de volumen. No afirmo un incumplimiento físico: la clasificación correcta para esta comprobación independiente es **evidencia insuficiente**, y bloquea usar el PASS G2 como fundamento ratificado de P4.

### MAJOR R3-002 — replay determinista P8 aprueba salidas terminales divergentes

El contrato P8 exige deterministic replay como gate (`openspec/changes/p8-wide-rpm-performance/specs/p8-wide-rpm-performance/spec.md`, requisito “measured gates and accounting”, líneas 60–75). En `motorsim/p8_performance.py`, `run_anchor` ejecuta `_run_once` dos veces; `deterministic_replay.state_equal` compara solo `p7_ledger` y `W_cycle_J`, mientras `metrics_equal` compara trabajo, presión máxima y residuos de masa/energía. No compara entrega fresca, cortocircuito ni el estado terminal completo entre esos dos replays. La comparación de restart es dentro de cada ejecución y no cubre esta divergencia entre ejecuciones.

Reproducción exacta, sin campaña física, desde `E:\dino\Dino`:

```powershell
.venv\Scripts\python.exe -c "import json,copy; from unittest.mock import patch; import motorsim.p8_performance as p; a=json.load(open('results/p8-wide-rpm-20260927/anchor-2500.json')); b=copy.deepcopy(a); b['fresh_mass_delivered_kg']=a['fresh_mass_delivered_kg']*2; b['fresh_short_circuit_mass_kg']=a['fresh_short_circuit_mass_kg']*2; run=patch.object(p,'_run_once',side_effect=[a,b]); run.start(); r=p.run_anchor(2500); run.stop(); print({'changed_delivery':a['fresh_mass_delivered_kg']!=b['fresh_mass_delivered_kg'],'changed_short_circuit':a['fresh_short_circuit_mass_kg']!=b['fresh_short_circuit_mass_kg'],'deterministic_replay':r['deterministic_replay'],'gate':r['gates']['deterministic_replay']})"
```

Salida: entrega y cortocircuito cambiaron, pero `state_equal`, `preparation_state_equal`, `metrics_equal` y `gate` resultaron `true`. Esto demuestra una falsa aceptación posible del gate, no divergencia observada en la campaña histórica.

## Estado por fase y límites de esta pasada

- **C3-R5:** el agente de solo lectura comprobó el artefacto LFS local y su SHA-256 `cf51eafd6a8058afb325278bf0dc5a2db241dff49d82c014f83d90a29b7536cb`; verificó 777 pasos, 100 celdas, duración 0–0.003 s, retorno causal en `0.002654656914619853 s`, conservación recalculada máxima `6.964551734577821e-16` y cero discrepancias B0/B1/B2 en las comparaciones examinadas. El runtime binding de siete componentes no se completó en R3 por el límite de ejecución del agente. C3 no se vuelve a marcar PASS por esta revisión.
- **P4 conservation/restart:** la auditoría de conservación G2 está bloqueada por R3-001. No reconstruí la matriz completa P4 ni ratifiqué restart/determinismo P4.
- **P5–P7:** el agente de solo lectura ejecutó 99 pruebas offline focales y revisó contratos/evidencia de provenance; estos resultados no equivalen a ratificación, porque P4 no supera el gate independiente. No se completó cada prueba de restart/ledger de esas fases.
- **P8:** evidencia histórica de anchors y seis hashes de provenance fueron verificados por el agente; el código productivo `motorsim/` no cambió desde `437a66f`. La campaña completa excluida no se repitió. R3-002 bloquea su gate de replay. Se conserva `BOUNDED_TRANSIENT_INDICATED`; no se afirma periodicidad ni validación experimental.
- **Pruebas y OpenSpec:** 82 pruebas focales ejecutadas en este contexto pasaron; 99 pruebas offline adicionales reportadas por el agente P5–P8 pasaron, con la campaña P8 excluida. Validación OpenSpec estricta PASS para `p4-escape-1d`, `p5-intake-transfer`, `p7-prescribed-heat-burn` y `p8-wide-rpm-performance`; P6 está especificado como parte de `p5-intake-transfer`, no como cambio separado. Git LFS fsck PASS.

No se ejecutó P9 ni se cambió código, física, solver, contrato o threshold. La ratificación requiere evidencia G2 que permita reconstruir balances físicos y corregir el gate de igualdad del replay P8, seguido por una nueva revisión independiente. R1 y R2 permanecen intactos.
