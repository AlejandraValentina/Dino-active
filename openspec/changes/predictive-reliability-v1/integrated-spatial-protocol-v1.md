# Integrated spatial diagnostic — preregistered before calculation

2026-10-26. The connection numerical gate is complete (`cd610b2`), preserving
legacy default and rc7. Isolated spatial gate: exact cell averages, observed
order >2.12 for gas/species/acoustics; 31 checks including Sod and positivity.

Use the same original A9000 native configuration, same independent initial
states and two revolutions as integrated-port-protocol-v2. Cases:

1. Equivalent-nozzle coupling + first-order space, maximum 0.5 degree.
2. Same coupling + opt-in MUSCL primitive/species candidate, maximum 0.5 degree.
3. Same coupling + MUSCL, maximum 0.25 degree for time sensitivity.

Only the reconstruction descriptor differs between cases 1/2; only maximum step
differs between 2/3. Actual CFL, periodic detector, EOS, physical geometry, reed,
combustion, thermal and scavenging models remain unchanged. V8 explicitly labels
the new numerical capability and rejects unsupported readers; V7 labels nozzle
only. Both legacy choices remain available. No Desktop changes or warm start.

Budget and conservation/restart acceptance from integrated-port-protocol-v2 are
retained: 240 s, 10000 steps, 0.1 GiB artifacts per case, storage preflight;
normalized mass/species <=1e-9, energy <=1e-8; exact checkpoint replay. Maximum
terminal time-refinement discrepancy <=1% using the same physical norms. No
stationary power, periodicity, experimental precision or target power claim.

Compare case 1's actual terminal physical state/ledger against the recorded
pre-spatial nozzle result; expect bit-identical physical results since the
reconstruction is disabled. Do not rewrite source/checkpoint bindings to pretend
these are the same producer. Compare cases 1/2 physically, not by power alone.

Replay the second coarse-MUSCL cycle and use the existing offline primary
auditor, including actual nominal proposals and retries. Reuse recorded stages
and their hashes, without a duplicate raw trajectory or new RPM campaign.
Record positivity rejections and any domain errors. A failed criterion remains
failed; no clipping states, flow or species, no relaxed threshold. If an actual
defect appears, preserve its exact input and fix it before dependent work.

Review is SELF_REVIEW. Experimental accuracy and the real-port loss closure
remain unvalidated. Spatial smooth-wave convergence is numerical verification.
