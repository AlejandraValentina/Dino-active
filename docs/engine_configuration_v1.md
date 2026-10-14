# ENGINE_CONFIGURATION_V1 backend

This backend provides data services for a future Windows UI. It does not add a
GUI, run a campaign, or change solver equations. Public entry points are:

- `motorsim.engine_configuration.create`, `validate`, `identity`, and
  `to_solver_configuration` for strict `IntegratedEngine2T` documents.
- `motorsim.engine_variants.variant`, `escape_sections`,
  `replace_escape_sections`, and `compare_configurations` for explicit patches
  and supported escape geometry.
- `motorsim.engine_project.create_project`, `load_project`, `save_project`,
  `duplicate_project`, and `compare_project_engines` for editable projects.
- `motorsim.engine_results.import_report` and `compare` for the existing
  versioned IMPL2 JSON report or its CSV plus mandatory aggregate JSON companion.

Configuration validation delegates capability, topology, boundary, combustion,
port, thermal and geometry validation to the native
`IntegratedEngine2T.from_configuration_dict` constructor. It constructs no
solver steps. The editable document separately requires an explicit
`MECHANICAL_LOSS_MODEL_V1`, operating conditions, unit declaration, and
provenance. Native geometry follows the solver's existing field conventions;
lengths explicitly suffixed `_mm` are millimetres and the remaining native
fields retain their declared SI/native units. Unknown native fields are rejected
by the native schema.

Exhaust profiles are ordered circular, axisymmetric, piecewise-linear diameter
sections. Each section becomes one finite-volume cell and uses exact linearly
varying circular-frustum integration for volume and centroid. Editing preserves
the existing number of exhaust cells so initial-state remapping stays
unambiguous; it rescales each cell's extensive species inventory with its new
volume at the unchanged primitive state. The representation does not implement
branch junctions, non-axisymmetric ducts, spatially resolved wall heat transfer,
or multidimensional gas dynamics. Those capabilities are rejected rather than
approximated. One cell per section is the existing supported resolution, not a
claim of mesh convergence.

Projects store only external result references and never cycle primaries or
checkpoints. Writes use a same-directory unique temporary file, flush/fsync,
and atomic replacement. The project loader validates nested engine identities.

Curve imports preserve point classifications, periodicity classification,
hard-gate objects, metric status/reason, hashes and units. Values that are
undefined or invalid remain `null` gaps. No interpolation or smoothing is
performed. `PERIOD_1` is retained as periodicity classification and does not
assert that every hard gate passed. The supplied IMPL2 dataset remains synthetic
and has no experimental validation claim.

The future Windows frontend should call these backend APIs and display
`validation_state`, per-point metric status/reason, scientific classification,
identity hashes and external-result provenance. It must not infer solver
support from editability alone.

Powervalve endpoint rounding is documented separately in
`results/engine-configuration-v1/powervalve-endpoint-roundoff-proposal.json`.
It is a proposal only; the three historical IMPL2 points remain
`NUMERICAL_INVALID`, and no solver or campaign files are changed here.
