# DINO_TUNING_WORKBENCH_V1 implementation receipt

## Scope and classification

The DWT-F0 through DWT-F4 source implementation is complete. No simulation or campaign was started, and no solver, physical model, mesh adapter, periodicity rule, hard gate, or scientific artifact was changed. Package and desktop interaction acceptance remains blocked, so the objective remains `DINO_TUNING_WORKBENCH_V1_PARTIAL`.

## Implemented behavior

- D1 refreshes exhaust overlay variants after project changes. D2 maps changed escape paths to the correct section. D3 estimates one-run time from a comparable cell count or the documented 30-second fallback, with an explicit capped suggestion that never changes the budget automatically. D4 scales pressure plots to the available finite data and keeps missing values as gaps. D5 guards unsafe artifact roots without moving existing data. D6 redirects test QSettings to temporary isolated INI storage. D7 uses the same project variant key across workspace areas. D8 was reproduced: `ResultsPage.metric` shadowed `QWidget.metric()`; the selector is now `metric_selector`, leaving Qt's method callable.
- Component tabs expose the existing engine, ports/distribution, mechanical-loss, exhaust and combustion inputs. Port angles and exhaust geometry come from current backend data; a single station-diameter control preserves shared station continuity.
- The integrated shell keeps project/variant context, baseline preference, build, results, guarded single-run controls and evidence available. Baseline is a per-project QSettings preference, not a project-file or configuration mutation. The 980×680 layout stacks build and results vertically.
- Run history can open one or compare two read-only EXPLORATORY runs, including runs in different artifact directories. The conventional importer re-audits primaries. Engineering views retain exact discrete cell/angle samples and do not interpolate; undefined power/torque remain undefined.

## Verification performed

- `python -m pytest tests/test_dino_workbench_f0.py tests/test_dino_desktop_ux_v2.py -q`: **26 passed**.
- Focused desktop/history tests: **6 passed, 1 skipped, 22 deselected**. The skipped test requires an external IMPL2 artifact root (`tests/test_dino_desktop.py:170`).
- Existing external EXPLORATORY artifacts were re-imported with the conventional independent importer from `E:\Dino-artifacts\dino-design-validation-v1`. Two real 3000 RPM runs (Escape original and Escape modified +20 mm) yielded two points and two traces; both audits were recomputed and PASS. Both remain classified `EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED`, with periodicity `NOT_EVALUATED`. This was artifact verification only, with no solver execution.
- `openspec validate dino-tuning-workbench-v1 --strict`: PASS before the final receipt edit; rerun after this edit.
- Program-status `brief`, `check`, and `promote` were run at session start. Final `check`/`promote` are required after recording the blocked package task.

## Windows TRIAL package

Built from dirty-tree HEAD `7366284674abd9cdf5fa59f10354f823cec1ea3c` using `packaging/build_windows.py --trial`:

- Folder: `dist/MotorSim-0.1.0-rc6-windows-x64-73662846-trial-20261014T175142Z/MotorSim`
- ZIP SHA-256: `5282306dde23983a64603acc134b1e0cff971508a3af8e32946b95ca49200acf` (ZIP integrity check PASS, 299 entries)
- New bundle executable SHA-256: `Dino2T.exe A717D0EF14E4F355D97AA371383896E3D893D298C85BAF3F4DAE8B2E3247CE78`; `MotorSim.exe 9337D35857C7B2CE4E503BE220EA138699F1C51917194CAD2BF49B1C58EF29A8`; `MotorSimWorker.exe 8914302FC647E306A5C56C388ACAD7DD3B9483F654EDE8736BEBABCD5A0E5112`.
- Startup outside the repository working directory was observed: the process created a responsive window titled `Dino 2T — dino-project`, and it was closed. This is a startup smoke check only.
- The earlier distribution remains unchanged: `MotorSim.exe 9A78CFB85ADC1DFC4DFD03841C9F36E529708164ADD892B13B38F9F65A080A8E`, `MotorSimWorker.exe BB15FA861D1DED09F96BA1DEA662406EF944F13CA5E6455CAD1730F63D761C44`, and `Dino2T.exe 5A05133ECCF07248476A9BCEC114A056AA898191389444F75B58C5D408F5A063`.
- The new bundle is correctly marked TRIAL and `source_dirty=true`. The packaged workflow to open the example, select actual runs, inspect results, compare, and capture valid screenshots has **not** been completed. Desktop automation was inaccessible in the locked Windows session, and attempted captures contained placeholder glyphs; those unusable images were discarded. No such image is accepted as visual evidence.

## Remaining blocker

`DWT-PACKAGED-ACCEPTANCE` is `BLOCKED_LOCAL` on an interactive, unlocked Windows desktop session. Its unblock task is to repeat the real EXE workflow and capture usable 1360×900 and 980×680 evidence after that session is available. Until then the workbench is **PARTIAL**, not READY.
