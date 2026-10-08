# Diseño del programa

Este cambio es el registro durable único de `MOTORSIM_2T_COMMERCIAL_CORE`; no
reemplaza ni edita contratos históricos. Los componentes nuevos se separarán en
módulos tipados con esquema/versionado explícito, conservarán su configuración
primaria y provenance, y se conectarán a la integración P5-C/P6 existente cuando
la topología del componente sea compatible. No se duplica el solver 1D.

El harness de referencia continúa independiente de anchors P8 y de E13
histórico. Su contrato congelado actual conserva CFL 0,4, 400 ciclos y los
umbrales ya preregistrados. El bloqueo KT100 actual ocurre en la frontera de
reservorio existente; ninguna fase posterior puede cambiarla de forma implícita
ni reclasificar los recibos r5. Las fases independientes pueden avanzar con
fixtures analíticos y evidencias propias.

## Fronteras externas versionadas

`LEGACY_CHARACTERISTIC_V1` conserva literalmente las fronteras históricas
`open`, `nonreflecting` y `reservoir`. El nombre histórico `nonreflecting` se
describe semánticamente como `EXTERNAL_STATE_RIEMANN / FARFIELD`; esta etiqueta
no cambia sus ecuaciones ni reinterpreta evidencia previa.

`OPEN_END_PLENUM_V2` es una capability opt-in nueva para una abertura a una
atmósfera o plenum grande en reposo. Es un `SYNTHETIC_ASSUMPTION`: su admisión
isentrópica y sin pérdidas no representa un carburador real calibrado ni datos
del Walbro WB40. No modifica V1 ni cambia silenciosamente las terminaciones de
Fixtures A/B. La presión del reservorio es la presión ambiente estática y sus
presión/temperatura de estancamiento y composición son entradas explícitas.

Sea `n` la normal unitaria hacia afuera del dominio, `w_i=n*u_i` la velocidad
normal interior y `J_i=w_i+2*a_i/(gamma-1)` el invariante acústico saliente.
Con `K_i=p_i/rho_i^gamma`, la cara del lado interior para una presión candidata
`p` es

`rho_i*(p)=(p/K_i)^(1/gamma)`,
`a_i*(p)=sqrt(gamma*p/rho_i*(p))`,
`w*(p)=J_i-2*a_i*(p)/(gamma-1)`.

Para flujo saliente subsónico se impone `p*=p_amb`, se conserva `K_i` y se usa
`w*=w*(p_amb)`. Si el estado de presión ambiente pide `w* >= a_i*`, la salida
queda estrangulada: se fija `a*=J_i*(gamma-1)/(gamma+1)`, `w*=a*` y se obtiene
`p*` de `K_i`; por tanto la presión de cara puede superar a `p_amb`, como
corresponde al límite crítico. En la cara el estado transportado usa la
densidad/entropía interior.

Para flujo entrante subsónico, el lado interior conserva `J_i` y `K_i`, mientras
el lado del reservorio conserva su entropía independiente
`K_0=p_amb/rho_0^gamma`, `rho_0=p_amb/(R*T_0)`. Se resuelve la raíz única en el
intervalo donde `w*(p)<0` de

`cp*T_0*(p/p_amb)^((gamma-1)/gamma) + w*(p)^2/2 - cp*T_0 = 0`,

con `0 < p <= p_amb`. La cara de contacto comparte `p*` y `w*`, pero no fuerza
igualdad de densidad/entropía: el estado que dona masa usa
`rho_0*(p)=(p/K_0)^(1/gamma)`. La raíz es única porque la función es
estrictamente creciente donde `w<0`; el extremo inferior es el punto `w=0` y
el superior es `p_amb`. Si el flujo requerido excede el límite, se usa el
estado sónico isentrópico del reservorio (`M=-1`,
`p*=p_amb*(2/(gamma+1))^(gamma/(gamma-1))`) sin forzar el invariante saliente,
que deja de entrar desde el interior al alcanzar el choke. No existe área,
coeficiente de descarga ni pérdida implícitos.

En inflow, `h* + w*^2/2 = cp*T_0`; en outflow se conserva la entropía del
interior y la energía total proviene de ese estado. La orientación se transforma
solo con `w=n*u`; el flujo axial usa la velocidad `n*w`. El donante de especies
es la composición del plenum para inflow y la interior para outflow; el flujo de
especie usa exactamente el flujo másico común. El flujo de momento incluye `p*`
explícitamente, y la reacción de presión sobre el dominio por unidad de área es
`-n*p*`; los ledgers integrados aplican el área una vez.

Con entropías iguales `K_i=K_0`, la rama subsónica reduce a la frontera de
reservorio V1. La presión fija en el outflow tiene reflexión acústica de presión
de magnitud unitaria en el límite lineal; esta respuesta forma parte del modelo
de abertura a plenum y no se etiqueta como frontera no reflectiva.

La interfaz futura `RESTRICTED_NOZZLE_V1` queda definida solo como un contrato
de entradas requerido (`Cd`, área efectiva y provenance) y un nombre de
capability; no tiene implementación ni valores predeterminados. No se añade
`MASS_FLOW_INLET`.

La preregistración completa, su decisión de provenance, los gates y el conjunto
de tests inmutable están en
`docs/gasdynamic/open_end_plenum_v2_preregistration.md` y su receipt JSON en
`results/2t-commercial-core-20261002/preregistration/open-end-plenum-v2.json`.

Toda métrica nueva documenta ecuación, dominio, unidades, especies/ledgers de
origen y comportamiento ante denominadores cero antes de usarla en campañas.
Todo estado persistente importante prueba round-trip, restart y replay. La
configuración experimental P9 permanece pendiente de datos y se mantiene fuera
de la ejecución automática.

## Fases y dependencias

Las fases se registran en `tasks.md`. Un bloqueo local conserva su evidencia y
permite continuar fases independientes. `Commercial Core Ready` requiere la
integración completa definida por la autorización de la usuaria, incluidos dos
casos de referencia trazables; un módulo aislado no satisface ese gate.

## Geometría de puertos `GENERIC_2T_PORTS_V1`

La primera capacidad se implementa como configuración JSON independiente del
Project v6: los proyectos históricos conservan su esquema y cálculos actuales.
La configuración identifica conductos por `id`/rol y lumbreras por `id`, rol,
función geométrica, coeficiente de descarga y provenance. Una lumbrera bridged
se representa como sus aperturas individuales con un `group_id` común; las
áreas se suman por conducto sin fingir que el puente es otra ventana.

Las ventanas rectangulares usan posición axial desde PMS, positiva hacia PMI,
mm desarrollados y `piston_position` existente. Para transfer/escape,
`Aeff=Cd*w*max(0,min(h,x(theta)-top-roof_travel*position))`. Para piston-port
intake se reutiliza `intake_results`: `d=top+h-skirt`,
`Aeff=Cd*w*max(0,min(h,d-x(theta)))`. El coeficiente es una entrada positiva
finita; no se estima ni calibra. Perfil explícito: knots finitos 0–360°,
estrictamente crecientes, área no negativa, extremos idénticos; evaluación
piecewise-linear, periódica. Los perfiles explícitos se reservan a aperturas de
escape; transfer e intake conservan geometría de ventana/piston-port. Muestreo
derivado a cada grado inclusive sirve para visualización/persistencia, mientras
el evaluador continuo y los eventos exactos
son la fuente para integración futura.

La serialización incluye SHA-256 canónico de geometría/config y de perfiles
derivados; al leer se regeneran y comparan los perfiles. Estos hashes prueban
binding/integridad del artefacto, no son evidencia física. El coeficiente y el
área no se conectan al P5-C histórico en este primer tramo; integración con
topología variable requiere un adaptador nuevo y pruebas de ledgers por ducto.

## Métricas de scavenging `MOTORSIM_2T_SCAVENGING_METRICS_V1`

Se usan masas de especies P6: `F=fresh_air+fuel`, `R=residual`, `M=sum(especies)`.
Fresh delivered y fresh short-circuit proceden de los ledgers P6 por dirección.
`Fret` es la especie fresca presente en el cilindro al cierre de la última
apertura de escape; `Mref=rho_amb*pi*bore²*stroke/4`. Delivery ratio=`Fdel/Mref`;
trapping efficiency=`Fret/Fdel`; scavenging efficiency=`Fret/Mexhaust_close`;
charging efficiency=`Fret/Mref`; trapping ratio=`Fdel/Fret`; residual fraction
`=Rexhaust_close/Mexhaust_close`; purities at transfer/exhaust close are the
respective fresh mass fractions; short-circuit fraction=`Flost/Fdel`. Zero
denominators return `UNDEFINED/ZERO_DENOMINATOR`; no clipping to [0,1] and no
substitution of zero. A model output outside a familiar efficiency range remains
visible to expose ledger/state mismatch. `Fret` and `Flost` remain separately
reported masses.

The trajectory adapter accepts resolved scheduler-angle identities from the
geometry layer, requires exactly one snapshot at each closure, binds the last
snapshot to the terminal gas/species state, and recomputes fresh delivery/loss
from cumulative P6 ledgers. It rejects a missing event, nonmonotone trajectory,
terminal mismatch, bool-as-number, or stale cycle summary; it never interpolates
across a closure event.

## Reed `STATIC_REED_V1` / `DYNAMIC_REED_V1`

Each synthetic/configured petal supplies `m`, pressure area `Ap`, effective
flow width `w`, spring `k`, damping `c`, lift limit `h`, flow coefficient `Cd`,
restitution `e`, and provenance. Positive `dp = p_upstream - p_downstream`
opens the valve. Static lift is `clamp(dp*Ap/k,0,h)`; static reverse flow is
blocked. Dynamic state follows `m*x''+c*x'+k*x=dp*Ap` at constant dp during a
solver step. Use the closed-form damped linear-oscillator solution between
contacts; detect contact times from monotone intervals separated by exact
velocity extrema and bounded bisection, apply configured restitution, then
advance the remaining step. At a stop where acceleration points outward, hold
the petal there until the force releases it. `Aeff=Cd*w*x`; bank area is the
sum of petal areas. Existing `simulation.restriction` computes mass/energy/fresh
flux. Static mode gates reverse flow; dynamic mode allows transient reverse
flow while open and records no ledger itself. All coefficients are user/model
inputs with provenance; no value is fitted. The standalone state model does not
modify P5/P6 and requires a later stage-coherent integration phase.

## Expansion chamber geometry and trace adapter

`ExpansionChamber` is a typed, provenance-bearing assembly of continuous
conical sections (header, diffuser, belly, baffle cone, stinger, silencer,
tailpipe or generic cone). It uses the accepted `gas1d.mesh.segments_mesh`
builder for exact frustum volumes and shared face areas. It does not implement
a second gas solver. `map_solver_state` consumes the existing quasi-1D
primitive trajectory to expose pressure, temperature, Mach, mass flow and
left/right characteristic speeds. Optional wave decomposition is explicitly
linear, isentropic and relative to a supplied base state. Reflection timing is
an estimate obtained by integrating characteristic speeds to a named section
station; reflected amplitudes remain the solver's responsibility. Neither
trace adapter nor geometry changes P4/P5/P6 contracts or the product project
schema.

## Thermal prescribed-wall transfer `MOTORSIM_THERMAL_V1`

Each configured surface has explicit area, provenance, `CONSTANT_H_V1`
coefficient, and exactly one wall-temperature source: a fixed kelvin value or a
bounded RPM/load map with bilinear interpolation. The model evaluates
`Qdot_gas_to_wall = h*A*(Tgas-Twall)`. A cycle ledger integrates the supplied
ordered crank-angle samples by trapezoids using `dt=dCA/(6*RPM)`, reports each
surface and total signed energy, and requires a complete specified cycle. Map
extrapolation is rejected. This is prescribed-wall transfer, not a wall-capacity
model or a fitted heat-transfer correlation; upstream integration must supply
gas temperatures from the same physical solver stages and close the energy
ledger globally.

## Prescribed combustion progress `COMBUSTION_MODEL_V2`

One or two Wiebe components define weighted burn progress with explicit
ignition angle, duration, shape `a,m`, and delay. The normalized law reaches
unit progress at each component's end; optional scalar or bounded RPM/load
efficiency scales the total burned fraction. CA10/50/90 are roots of the
weighted normalized progress. This capability returns only dimensionless
progress/rate and crank-angle points. It does not convert P6 species or release
heat: fuel chemistry, oxygen availability, LHV and energy ledgers require their
separate approved contracts before coupled integration.

## Mechanical losses and indicated/brake conversion

`MechanicalLossModel` sums explicit nonnegative FMEP terms classified as
piston/ring, bearing/accessory, or pumping, each fixed or given by a bounded
RPM/load map and provenance. For a two-stroke cycle of 360 degrees,
`Wloss=FMEP*Vd`, `Wbrake=Windicated-Wloss`, `BMEP=IMEP-FMEP`,
`P=W*RPM/60`, and `T=W/(2*pi)`. Negative brake output is preserved and flagged;
the model never clips it or fits losses to a target. This arithmetic capability
does not add losses to the gas solver or imply a measured performance map.

## Fuel accounting `FUEL_ACCOUNTING_V1`

Fuel properties explicitly provide stoichiometric AFR and LHV with provenance.
The cycle adapter receives delivered/trapped P6 fresh-air and fuel masses,
plus the prescribed profile's final burned fraction, and checks trapped mass
does not exceed delivered mass. Short-circuited fuel is a separate supplied P6
species-ledger value; delivered-minus-trapped is reported only as fuel not
trapped, not mislabeled as exhaust short circuit. AFR and equivalence ratios are explicit; zero
fuel yields `UNDEFINED/ZERO_DENOMINATOR`. Delivered fuel defines fuel flow and
includes any delivered-but-untrapped short-circuit amount. Burned, trapped
unburned, not-trapped and short-circuited fuel are reported separately. Heat potential is
`burned_fuel*LHV`; it is bookkeeping only and is not coupled to the solver.
SFC uses the 2T one-cycle-per-revolution rate; brake SFC is undefined when
brake power is nonpositive.

## Crankcase geometry `CRANKCASE_MODEL_V2`

The V2 geometry reuses the established slider-crank position with explicit
bore, stroke, rod length and BDC free volume. `V(theta)=V_BDC+Vd*(1-x(theta)/S)`;
the derivative is analytic in time at supplied RPM, and compression ratio is
`V_TDC/V_BDC`. A small-link helper delegates bidirectional pressure flow to the
existing 0D restriction, preserving its upstream donor and fresh fraction. This
is not a P5-C stage extension: wall heat remains a separate prescribed model,
and actual intake/transfer topologies still require global stage ledgers.

## Intake volumes and junctions `MOTORSIM_NETWORK_COMPONENTS_V1`

Network configuration describes explicit plenum, airbox and boost-bottle
volumes plus neck/junction area, effective length and provenance. Atmosphere
defaults to P6 species `(fresh_air=1,fuel=residual=burned=0)` while pressure and
temperature remain explicit. A volume/duct exchange reuses the existing P3
Riemann interface for gas flux and P6 `donor_species` for four-species flux;
the adjacent finite volume receives exact opposite extensive increments. A
lumped Helmholtz frequency is an estimate using the caller's declared effective
neck length, with no hidden end correction. This network description does not
yet add its nodes to the production P5-C SSPRK state or global campaign ledger.

## Exhaust powervalve geometry `POWERVALVE_GEOMETRY_V1`

The powervalve maps RPM to a bounded roof position using piecewise-linear
interpolation within the configured RPM domain; extrapolation is rejected.
Position `0` is the fully raised/open roof and `1` lowers the roof by the
configured `roof_travel_mm`, reusing the generic port geometry's existing
definition. It can target only the declared movable main rectangular exhaust.
Port area and event angles are then computed by `TwoStrokePortSet`; no servos,
control dynamics, or calibrated RPM values are added.

## Unified engineering outputs `MOTORSIM_ENGINEERING_OUTPUTS_V1`

The JSON-ready output binds a strict 360-degree 2T convention, RPM/cycle index,
explicit P4 dependency status, crank-angle samples, supported signal names,
units, source labels and cycle metrics. Undefined ratios carry `null`, status
and reason. It rejects unknown channels, nonfinite/bool values, incomplete
cycle spans and altered units. Periodicity defaults to `NOT_EVALUATED`;
experimental validation remains `NOT_PERFORMED` and predictive validation
`NOT_CLAIMED`. Channels remain optional until a producing solver path exists.

The fixed V1 contract remains unchanged and V2 remains available unchanged.
The integrated cycle collector now uses
`MOTORSIM_ENGINEERING_OUTPUTS_V3`, which retains V2's configuration SHA-256 and
path-addressed duct-cell/face channels while correcting fuel and scavenging
metric semantics. V3 calls the sum of positive fresh-air-plus-fuel crossings
into the cylinder gross delivery; recrossings are not tracked as unique
molecules. Short-circuit mass is the gross outward fresh species crossing the
exhaust while transfer and exhaust areas are open; reverse exhaust flow is not
counted. The gross intake air/fuel ratio describes only intake-boundary species
delivery, not trapped or burned AFR. ISFC/BSFC use the prescribed P7 fuel
pseudo-species sink and remain undefined with zero sink or nonpositive power.
That sink is bookkeeping, not experimental fuel burn. V3 continues to
re-integrate work, species/external exchange, P7/thermal sources and energy
conservation from saved SSPRK2 stages before building the artifact; cycle
summaries are cross-checks, never the output authority.

## Exploratory measurement import `MOTORSIM_MEASUREMENT_DATA_V1`

The additive importer handles pressure traces (cycle/angle/absolute pressure),
dyno torque and dyno power as strict CSV schemas. Metadata declares source,
configuration, conditions, value/uncertainty units, angle period and convention,
and provenance; raw CSV bytes are retained and bound by SHA-256. Only exact
coordinates overlay; no interpolation or condition equivalence is inferred.
Bias, MAE, RMSE and uncertainty-normalized RMSE are descriptive. Every result
is `EXPLORATORY_COMPARISON`, not validation-eligible, and the module does not
call, edit or feed the frozen P9 pipeline.

## Generic integrated 2T stage graph

The new orchestration is separate from historical P5/P6 campaign products.
It reuses the existing `IdealGas`, finite-volume meshes, HLLC face flux and
P3 Riemann interface. Each path has a stable id and role; the core requires
one intake, one exhaust and at least three transfer routes. One immutable
stage state feeds all boundary and internal faces. The resolved Euler mass,
momentum and energy flux is shared by connected cells/chambers, while four
extensive species masses use the existing P6 donor-selection function and the
same resolved mass-flux sign. The passive scalar slot is derived as total mass
density for compatibility and is never advanced as species authority.

The accepted state records two stage evaluations, exact stage geometry, CFL,
external exchange, chamber volume work and primary face/species traces. A JSON
checkpoint is tied to explicit caller-supplied geometry identity, meshes,
topology, EOS, boundary conditions, CFL policy and initial state. Restore
validates the candidate before installing it, including wrapped/unwrapped angle
agreement and crankcase/cylinder volumes at the restored angle. The caller's
geometry identity is a declared binding, not a proof of arbitrary callback
equivalence. The duct CFL includes both local wave-speed/width and
area-volume/face-wave-speed bounds; 0D chamber depletion also constrains the
step. The optional existing quasi-static reed resolves effective intake area
from each shared stage's duct and crankcase pressure. This first implementation
is a conservative gas/species foundation with prescribed `ThermalSystem` sources
evaluated from the same stage states; each surface requires an explicit
chamber or `duct_id:cell_index` location. Reed mechanics, combustion, complete
fuel conversion, periodic-cycle evidence and the complete engineering
collector remain open integration work. Existing reservoir-boundary
inconsistency is not hidden by an automatic fallback. AUD-11's human decision
selected CASE B and the additive `OPEN_END_PLENUM_V2` capability is implemented
under its own preregistered contract; its analytical tests pass. The single
preregistered KT100 V2 campaign did not emit cycle primaries because the
evidence writer failed after angular advance, so KT100 remains unqualified and
the campaign result is a local evidence blocker, not a boundary-physics verdict.

The integrated geometry adapter also binds every existing generic port duct
to one named integrated path. Port areas are accumulated by the mapped route;
the existing `PowerValve` may replace the configured main-exhaust roof at the
stage RPM before resolving its area. An existing multi-section
`ExpansionChamber.mesh()` is accepted as the exhaust path mesh. These bindings
are exercised together at stage resolution, but they do not yet establish a
complete angular cycle or exact scavenging closure. The open-end reservoir
capability is separately versioned and does not alter these bindings.
The duct-to-path mapping is copied into an immutable view at construction, so
later mutation of the caller's dictionary cannot diverge stage routing from
the checkpoint identity.

The integrated network path supports finite gas volumes at distinct external
duct endpoints: intake-left and exhaust-right. The existing P3 interface
resolves one mass, momentum, total-energy and donor-species flux per SSPRK2
stage; exact opposite mass/energy/four-species rates update each volume and its
duct. Volume states, fixed geometry, connection definitions and initial
compositions are bound into checkpoint identity, global inventories and cycle
reconstruction. The legacy `intake_plenum` input normalizes to the same generic
binding. These connections do not add an atmosphere-to-plenum boundary or
choose new generalized reservoir semantics. Each connection uses the existing
ideal, massless P3 Riemann interface: `effective_length_m` is retained as
geometry/provenance but does not add neck inertance or acoustic propagation to
this integrated path. The checkpoint schema is V7 and intentionally rejects
V6 checkpoints whose configuration identity did not contain network endpoint
bindings. The current integrated topology does not support intermediate
volume-to-volume connections or multiple volumes on one duct face.

Integrated constructor configurations use
`MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V1` only when existing
`SliderCrankChambers2T` and `IntegratedPortBinding2T` jointly resolve every
moving volume and port area. The JSON captures exact constructor states,
meshes, four-species inventories, EOS, boundaries, network endpoint volumes,
and existing component parameters. Reconstruction uses an internal placeholder
callback fully shadowed by those two explicit models. Arbitrary callbacks are
rejected as non-serializable. A live-configuration fingerprint rejects steps,
checkpoints, restores, and exports after configuration drift so checkpoint
identity cannot silently describe different future behavior.

The integrated geometry resolver can also consume the existing `CrankcaseGeometry`
V2 plus a cylinder compression ratio. It derives both moving chamber volumes
and opposite volume rates at each stage's angle and RPM, while retaining the
existing pressure-volume work term in the common gas RHS. The resolved model
configuration is part of checkpoint identity; no independent kinematics or
energy update is introduced.

Integrated cycle evidence is versioned as
`MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V2` to add geometry-bound last-close
snapshots for aggregate transfer and exhaust duct roles. The cycle builder
derives event angles from the bound generic port set and resolves a configured
powervalve at cycle RPM. It accepts a snapshot only when the accepted SSPRK2
trajectory has one endpoint exactly at that angle. Variable-RPM cycles with a
mapped powervalve, missing closures, or missing/ambiguous event rows leave the
closure evidence unavailable. The collector uses snapshots only when the
caller also supplies a positive reference-charge mass; otherwise scavenging
metrics remain explicitly undefined. It never interpolates event states, and
unavailable evidence cannot inherit metrics from another cycle.
Engineering trace rows at step starts pair the stage-start state with its own
stage-start face evaluation. The final row is rebuilt by a read-only RHS call
from the accepted terminal state, rather than pairing that state with the
provisional SSPRK2 second-stage flux. Its P7 value is the instantaneous
prescribed request before a future-step availability limiter and is descriptive
only; it is excluded from all accepted-cycle integrals and conservation terms.

### Fuel library V1, independent of combustion integration

`FuelDefinition` is a versioned catalog record, not a per-engine bag of
untraceable numbers. Every simulation can freeze the selected ID/version, the
canonical full record and its SHA-256. User edits create a new version; built-in
profiles can be disabled but cannot be overwritten. Library persistence and
import/export use strict JSON schemas. Lubricant identity and premix ratio are
separate future interfaces; neither is part of the fuel record.

The initial Uruguay catalog records only documented identity and RON for ANCAP
Super 95 and Premium 97. The 2024-06 product specifications state maximum
ethanol/oxygen levels, not the batch composition; those maxima are not converted
into point values. Density, LHV, elemental composition and stoichiometric AFR
therefore remain null. A profile with missing stoichiometry/LHV cannot produce
chemistry-derived outputs. No modeled surrogate is introduced until an explicit
versioned assumption and source basis are registered.

`FUEL_LIBRARY_V1` may store explicit complete elemental mass fractions. When
stoichiometric AFR is absent, method
`ELEMENTAL_MASS_BALANCE_DRY_AIR_V1` calculates oxygen demand per unit fuel mass
as `n_C + n_H/4 + n_S - n_O/2`, multiplied by the O2 molar mass and divided by
the versioned dry-air oxygen mass fraction. Negative/nonpositive oxygen demand
is rejected. This definition-level derivation does not add reaction chemistry,
select a combustion event, alter the four P6 pseudo-species, interpret P7 `Q_F`
as chemical energy, or couple any energy release to the gas solver. Existing V4
pseudo-species ratios keep their separate name and meaning.

The built-in records preserve source URLs and the individual claims they
support. ANCAP product pages and 2024-06 datasheets are the primary source for
RON and published specification limits; the datasheets do not provide the
missing point properties needed for AFR/LHV calculations.

### Dynamic reed coupling preregistration

The next reed increment is registered in
`docs/gasdynamic/dynamic_reed_coupling_v1_preregistration.md` before any coupled
fixture run. `DYNAMIC_REED_HINGED_FLAP_GEOMETRY_V1` is a synthetic linear flap
with declared width/length, curtain area `Cd W x` and swept-volume coefficient
`W L/2`; the existing pressure-force area must match that swept coefficient.
The first verification target is a coupled pair of well-mixed gas control
volumes, not an undocumented real-engine layout. Both adjacent volume-work
terms, petal force work, SSPRK2 stage RHS, P6 donor species, and mechanical
dissipation are explicitly bound into one energy/species ledger. Stop-contact
stages are rejected atomically until a separately versioned event contract is
available. Existing static reed and standalone `DYNAMIC_REED_V1` behavior is
preserved. The preregistration is not evidence of implementation or acceptance.

The preregistered component exists as
`motorsim.reed_coupling.DynamicReedTwoVolumeCouplingV1`. It has its own global
mass/species/energy ledger, replayable local checkpoint and bounded synthetic
tests. The V1 engine binding now couples the intake duct's terminal 1D cell,
crankcase and petal in the common SSPRK2 stages. Its state/configuration schema,
variable endpoint volume, crankcase volume-work, CFL, checkpoint/restart, cycle
primary and V4 channels carry the synthetic geometry and mechanics. A full
synthetic cycle was rebuilt and its collector validated. This does not qualify
real-engine reed dimensions, KT100, periodic convergence or Commercial Core
acceptance; stop-contact stages remain rejected rather than clipped.

For the moving terminal cell, SSPRK2 updates extensive mass, momentum and energy
before recovering stage densities from the effective cell volume. Total mass is
derived from the four authoritative P6 species. This avoids a product-rule
roundoff mismatch between a density update and a changing cell volume. The
energy increment includes the explicit boundary pressure work `-p dV`; the
crankcase receives the opposite reed volume-work term, while petal spring/kinetic
energy and damping loss close the global balance.
