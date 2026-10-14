# EXHAUST_MESH_V1 Specification

## ADDED Requirements

### Requirement: Explicit versioned axial section refinement
The exhaust discretization MUST explicitly identify EXHAUST_MESH_V1 and the integer cell count (1, 2, or 4) for every named geometric section. Each section MUST retain its length, end diameters, interface continuity, conical/variable geometry, finite-volume face areas and control-volume volumes. The generated mesh MUST be deterministic and invalid resolutions or degenerate geometry MUST fail closed.

#### Scenario: Refine a variable-diameter section
- **WHEN** a named conical section is divided into two or four cells
- **THEN** face positions and diameters follow its axial profile, cell volumes sum to the exact frustum volume, and section endpoint/interface values remain unchanged.

### Requirement: Conservative initialization and area-aware solver binding
Mapping an engine state to a changed exhaust mesh MUST preserve total mass, each species mass, and total energy within the declared numerical tolerance. The integrated solver MUST use actual face areas in fluxes and its existing consistent quasi-1D geometric source. Any required equation change MUST be separately versioned and tested; no hidden correction is permitted.

#### Scenario: Split or merge section cells
- **WHEN** the same physical section is represented at 1/2/4 resolution
- **THEN** state and species quantities map conservatively and the existing area-dependent finite-volume formulation remains active.

### Requirement: Scientific identity and checkpoint isolation
The configuration/run identity MUST bind adapter version and source hash, per-section refinement, resulting discrete geometry, engine configuration, solver and boundary conditions. A checkpoint or project with incompatible mesh identity MUST be rejected; historical IMPL2 and DINO design artifacts MUST remain untouched.

#### Scenario: Restore an incompatible checkpoint
- **WHEN** a checkpoint was created with a different refinement or geometry identity
- **THEN** restore fails closed before advancing the solver.

### Requirement: Desktop mesh inspection
Desktop project editing MUST allow explicit per-section 1/2/4 resolution and expose total cell count, section/cell length, face area, cell volume and axial location, with invalid mesh warnings and rendered mesh boundaries. A chamber visualization MUST NOT imply experimental or physical validation.

#### Scenario: Inspect refined exhaust mesh
- **WHEN** the user selects a refinement
- **THEN** the preview displays the derived geometry and identity-bound mesh used by the solver.

### Requirement: Bounded mesh sensitivity evidence
An isolated diagnostic MUST compare escapes A and B at 1/2/4 cells per section under otherwise identical conditions and no more than 1800 seconds aggregate wall time. It MUST record geometry, mesh, CFL/accepted/rejected steps, conservation, physical-location pressure/flow comparisons, audit, runtime and terminal/convergence classification. Comparisons MUST use common physical coordinates or common section interfaces, never cell indices. Results MUST NOT be called spatially independent or design validated merely because six diagnostics completed.

#### Scenario: Compare refinement response
- **WHEN** the six short diagnostics finish within the budget
- **THEN** 1→2 and 2→4 sensitivity and A/B response are reported with convergence limitations explicit.
