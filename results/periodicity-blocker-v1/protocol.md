# Single discriminating continuation — fixed before execution

Owner scope: close or characterize periodicity using existing evidence, one bounded test, no RPM grid. Delivery2B remains functionally accepted; historical results are unchanged.

## Evidence and hypothesis

A_original9000 cycle30 fails57 metrics:44 residual/burned fractions,8 fresh-air fractions,3 exhaust-cell masses,2 global species. All pressure, temperature, energy and Mach-change metrics pass. Exhaust residual inventory falls from2.147g atcycle1 to1.014g atcycle30; exhaust mass2.089g, outlet40.283mg/rev, inlet37.329mg/rev. Instantaneous inventory/outflow residence estimate51.85revolutions=0.346s at9000; this is a throughput scale, not a convergence prediction. Thirtycycles are0.20s. At present residual efflux38.483mg/rev, declining as the front passes. No assumed exponential fit or guaranteed convergencecycle.

Hypothesis A: transport of initial residual gas through the large expansion chamber dominates the failures; finite-volume numerical diffusion broadens the front. Continue the identical state, allow that front to leave, and test the unchanged detector. B/C remain possible if drift stalls, grows, or violates conservation. D is not supported: every stored comparison recomputes identically; cell fractions use absolute0.002 and inventories use current cycle-start total mass as defined, without pressure-only substitution.

Source inspection: source-free exhaust species transport uses donor fractions and signed fluxes; subsonic open-end outflow prescribes ambient pressure while retaining interior entropy, reverse flow uses explicit atmospheric donor. Outlet species are pure air, not fuel; residual has no external inflow source. Exhaust thermal walls remain the existing fixed623K model. The balance reduction checks boundary transport separately from whole-system sources. This is self-review of producer diagnostics, not an independent audit or experimental validation.

## Frozen execution

- Only A_original9000RPM; same native configuration,44total/31exhaust cells,CFL0.4, all physical/control parameters unchanged.
- Parent: functional-exhaust-comparison-v1-20261022 / exploratory-workflow-v1 / functional-reed-125cc-v1 / ab-A-9000 / invocation-001.
- Manifest SHA256:9293e20061d83be13f1701d3fa2ce249dd84b4f0bbb487eeaf845da0dc6d941e.
- Checkpoint SHA256:1f06eacdc1bf87b5cb76c66e77067980647b26c90d24125e476f61de31fc5620,next_cycle31.
- Shared unchanged producer SHA256:0e67eee751bb8b3c0fae1885fb1b2db19acc61941e1b587518ecbe82e736bd5f.
- Existing runner `motorsim.engineering_point.run` with explicit parent manifest/producer. Exact snapshot restore, no reset or acceleration of species/temperature. Same explicit mechanical postprocessing model from parent,load1.0.
- Absolute finalcycle cap110, i.e.80additional cycles; new wall budget600s, sequential512MiB worker. Parent220.274s accounted separately; maximum820.274s combined producer wall. One invocation only, no automatic retry/extension. External storage `DINO_ARTIFACT_ROOT / periodicity-blocker-v1-20261023 / continuation-001`.
- Per-step existing CFL, positivity, memory and wall guards; existing conservation threshold1e-8. Per-cycle checkpoints. Stop on errors, time/cycle cap, or three consecutive complete V2 comparisons PASS (minimum10cycles already met).
- Run through run_logged with a650s outer emergency timeout. The solver600s cap governs normally; outer timeout never authorizes more solver time.

## Discriminants and acceptance

Recompute existing V2 comparisons; inspect all31exhaust cells and global inventories, cylinder/crankcase, work, delivery/short circuit and combustion diagnostics. Record species and energy/mass balances, pressure wave drift, work and trapped-air changes vs cycle30, timing and memory. Inspect fuel heat/trapped charge explicitly because the inherited P7 fields are zero under fuel-limited combustion. Three full comparisons PASS establishes only the implemented finite-resolution period-1 observation; it does not establish mesh independence, experimental validity or calibrated brake power. A bounded nonpass closes as unresolved with actual remaining metrics; no second campaign.

L0 before execution:19 detector/reference tests pass. Zero-step preflight restores exactly, validates hashes and mechanical model, rejects8000/10000RPM against9000checkpoint; availableRAM4873.59MiB exceeds512MiB. All30diagnostic file hashes and finalcheckpoint verified;720unique phase samples/cycle. Maximum exhaust-mass balance discrepancy2.433e-18kg and species2.169e-18kg. No solver/UI/library source edits.
