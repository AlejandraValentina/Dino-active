# Pressure-wave/outlet diagnosis and bounded integrated pilot, 2026-10-27

**Ready for a bounded engineering study of periodic convergence; not yet ready
for a claim of mesh-independent periodic results.** No demonstrated product
solver defect; no MUSCL/HLLC/transonic/plenum modification. SELF_REVIEW, L1.

## Propagation separated from reflection

A right-travelling Gaussian, eps=1e-5 about p=rho=1,u=0,gamma1.4, is compared
with independent linear acoustic cell averages. Pressure-release reflection is
negative for pressure and positive for velocity. Finite-amplitude O(eps^2)
terms and initial nonlinear averaging are below this measured grid error.
No experimental end-correction/radiation-loss claim is made by this ideal end.

|Cells|Incident pre-reflection L1/eps|Final reflected-field L1/eps|Reflected amplitude/eps|Reflected centroid phase error(s)|
|---|---:|---:|---:|---:|
|32|.017809|.040538|.733759|-.000686|
|64|.005824|.014986|.895548|+.000187|
|128|.001677|.004305|.963245|+.000118|

Final field is measured at t=.8; pre-reflection control at t=.2. Reflected sign,
amplitude and spatial norms improve. The centroid error is not strictly monotonic
in signed value; it is reported separately from amplitude. Halving time step at
128 cells gives final L1=.004210, amplitude=.963257, phase=.000115s. These fields
include propagation and reflection error; subtraction of two scalar norms is
not a valid isolated reflection-error estimate. No negative-reflection coefficient
is inferred by dividing two attenuated peaks. Incident and image fields and
velocity reference are recorded, allowing separate engineering interpretation.

## Reversal, donors and conservation

Direct boundary algebra covers three successive prescribed velocity reversals
(+/-.15), unequal interior/reservoir temperature, and velocities0,+/-1e-12.
Mass-flux sign and reservoir donor agree; incoming total enthalpy cp*T0 differs
by at most1.34e-15. Outgoing total enthalpy retains the actual interior gas
state (verified by a specific test). Production integrated species donor handling
uses the signed common mass flux and the proper four-species source. Acoustic
integration transports reservoir species on inflow and interior species on
outflow with identical stage fluxes in both cell update and ledger. Maximum
Euler/species conservation residual2.16e-15. Fifteen focused checks PASS,
including existing transonic integration tests, without changing frozen tests.

These are weak compressible waves plus direct reversal checks, not a nonlinear
integrated multiple-reversal/shock proof. No new simultaneous change of boundary,
transonic law or reconstruction was made. The full engine still needs coupled
mesh/time evidence in its own pulsating domain. Gross absolute boundary-transfer
field in the acoustic JSON integrates absolute **net boundary balance**, not the
sum of absolute flows through each end; use outlet_history for end-specific flow.

## Outgoing mass error and cancellation

A new time-resolved audit revisits the exact translating contact used previously.
Absolute integrated outgoing flux error on32/64/128cells is
.037364/.023376/.013885. Signed terminal mass errors are
.0013953/5.8665e-5/2.1791e-7. Early leakage and later underprediction cancel
strongly: the excellent terminal mass error alone would overstate local flux
accuracy. The absolute error also decreases, so improvement is not solely an
accidental final cancellation. Neither terminal balance nor this control proves
accurate instantaneous engine mass flow. Profiles/history remain available.

## First integrated periodicity verification

Configuration frozen to the original44-cell A9000 synthetic V2/MUSCL endpoint V2
run, rc7 untouched. Actual solver dependencies matched its successful source-bound
cycle2 audit. Reused **the same run's** cycle2 native checkpoint, never a different
RPM/mesh state. Detector history reconstructed from original cycles1/2 using the
unchanged native-checkpoint observation helper and PeriodicDetectorV2 thresholds.
Those observations are L1, not regenerated audited primary cycle trajectories.

Maximum10additionalcycles,240s overall,150s numerical admission time,16MiB,
native checkpoint every revolution. Result **TRANSIENT_AT_BUDGET**, elapsed150.05s,
nine complete new cycles3–11 and a partial cycle12 at4000degrees. Nine native
checkpoints restored successfully, detector snapshot replay verified. FAST partial
terminal plus exact accepted/rejected recipe preserved separately from native
checkpoints. No automatic budget increase or repeated simulation follows.

Cylinder work cycles3–11:81.37,114.29,131.15,138.51,139.98,139.14,137.28,
135.20,133.22J. Last comparison still fails210observables. Work remains transient;
no extrapolated final power or required remaining-cycle count is justified.
CSV records work/IMEP, equal-phase cylinder pressure and delivered fresh mass;
full checkpoint comparisons retain species/pressures/temperature and inventories.
Ledger residuals at stop: mass-4.61e-18kg, energy-5.58e-12J,
maxspecies3.26e-18kg (rounded conservative bounds).

## Remaining uncertainty and decision

The method can support a checkpointed, bounded study, but this pilot has **not
established periodicity**. Its44-cell mesh is not independent: prior44/88 tests
show material spatial state differences; prior time refinement was only transient.
Neither is a substitute for comparing periodic work, IMEP, pressures, caudals
and composition at matched cycles on multiple grids. A subsequent study must
preregister matched-phase temporal and spatial comparisons plus realistic costs,
retain full-observable convergence and source identities, and budget L2 replay
separately. No full RPM campaign, guessed experimental engine, warm-start or
predictive accuracy claim is admitted. This bounded pilot is closed at its limit.
