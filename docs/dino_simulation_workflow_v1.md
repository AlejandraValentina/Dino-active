# Dino 2T — DINO_SIMULATION_WORKFLOW_V1

This workflow connects editable engine projects and exhaust variants to the
existing `IntegratedEngine2T`. The Qt application does not contain a second
physical model.

## Start with the supported example

Open `examples/projects/dino-2t-starter.dino2t.json` from **Archivo → Abrir**.
The project and fuel snapshot are synthetic. In **Motor**, edit supported
engine inputs. In **Escape**, change the existing linear conical sections and
apply the change as a separate variant. The variant adapter rebuilds the
solver exhaust mesh from those lengths and diameters; section count and
continuity must remain supported. Unsupported shapes fail validation. The
profile is geometry only and makes no acoustic or power-gain prediction.
For a prebuilt geometry example, open
`examples/projects/dino-2t-exhaust-comparison.dino2t.json`: it contains the
original and +20 mm diffuser variants with separate validated solver
configuration hashes. Run each variant as its own explicitly confirmed local
execution, then load both `result.json` artifacts in **Resultados**. No results
are fabricated into the example project.

## Local exploratory run

Open **Simulación**, choose one RPM and a maximum cycle count, and review the
no-step preflight. A run is for exactly the selected project configuration and
one operating RPM. The confirmation dialog shows the configuration, operating
point, cycle horizon, time budget, sampled process-memory threshold, artifact
root and run ID. Selecting **Yes** is a separate explicit authorization for
that EXPLORATORY run. Saving a review request does not run the solver.

The default artifact root is `%USERPROFILE%\Dino-artifacts`; set
`DINO_ARTIFACT_ROOT` or choose another local directory to change it. Each run
is isolated under `exploratory-workflow-v1/<project>/<run-id>`. The project
file stores no cycle data. Each full cycle is written in the standard
IntegratedEngine2T primary format, independently replay-audited, and followed
by an atomic checkpoint carrying configuration, solver, model and project
bindings. Resume requires the same identity and verifies prior primary and
checkpoint hashes. **Cancelar** stops at a step boundary, rolls back an
incomplete cycle, and retains the preceding complete checkpoint.

V1 is intentionally limited to one sequential solver worker, one operating
point per run, at most 128 finite-volume cells, at most 111 cycles, at most
600 seconds, 256–4096 MiB of sampled process RSS and 512 MiB of run artifacts.
Preflight requires at least 512 MiB free at the artifact root. Time and RSS are
checked around solver steps; the RSS threshold is a cooperative supervisor
guard, not an operating-system Job Object hard cap, so a transient within-step
overshoot is possible. Do not use this mode for unattended or safety-critical
resource containment. VERIFIED is unavailable; exploratory results make no
scientific-validation claim.

Periodicity uses the existing `REFERENCE_PERIODIC_CONVERGENCE_V2` detector.
Until it identifies PERIOD_1 or PERIOD_2, periodicity-dependent brake metrics
remain undefined. `Results` can load multiple `result.json` files from
EXPLORATORY run directories for side-by-side comparison. It verifies the
manifest and result hashes and leaves undefined values as gaps; it performs no
interpolation and labels the curves provisional. IMPL2 historical results
remain available from their separate aggregate report.

## Identity and historic evidence

The effective RPM is bound into the solver configuration without changing
the saved project. The run identity includes project configuration, loss
model, fuel provenance and source hashes for the integrated solver, mechanical
loss model and power-valve model. A configured constant RPM is used for
power-valve map interpolation; exact map-domain validation remains in force.
This source change has a new solver identity and does not rewrite, migrate or
reclassify historical R2/IMPL2 evidence.

No EXPLORATORY path calls the FULL_RPM_SWEEP campaign runner or FAST_RECIPE.
The existing campaign gates and authorization remain separate. No run can
create a VERIFIED PASS or authorize RPM campaigns or KT100.

## Windows package

Use the pinned recipe in `docs/dino_desktop_v1.md` after committing the
workflow changes and using a clean Windows x64/Python 3.11.0 checkout. The
package carries the desktop starter project; large run artifacts remain in the
external artifact root.

Si se produce una caída entre la escritura atómica de una primaria/checkpoint y la actualización del manifest, el resume falla cerrado y conserva el artifact huérfano para revisión; no lo sobreescribe ni lo adopta silenciosamente.
Una segunda instancia que apunte al mismo project/run ID se rechaza mediante un lock exclusivo. Si la aplicación cae y deja el lock, el resume falla cerrado; comprobar que no haya un proceso activo antes de retirar manualmente ese archivo.
