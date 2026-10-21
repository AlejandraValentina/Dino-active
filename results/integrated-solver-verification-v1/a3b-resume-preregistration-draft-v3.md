# A3b T1-A resume preregistration — draft v3

**Status:** `DRAFT_NOT_FROZEN_NOT_AUTHORIZED`
**Recorded:** 2026-10-21T10:25:33Z
**Scope:** read-only preparation. No solver, no resume, no cap selection, no tolerance freeze, no claim.

This draft describes what a versioned A3b T1-A continuation would require. It is evidence for the owner decision `ISV1-A3B-AUTHORIZATION-DECISION`; it is not that decision and it authorizes nothing.

## Why the current checkpoint cannot simply be resumed

The T1-A checkpoint is valid (`next_cycle=3`, cycles `[1,2]`, both primaries audited PASS), but the v2 driver refuses it under any new protocol:

- `_load_checkpoint` compares the complete `bindings` object, including `protocol_sha256` and `driver_sha256`.
- `_binding` embeds both the protocol hash and the LF-normalized driver hash.
- `_load_ledger` rejects a ledger whose `protocol_sha256` differs from the v2 hash.
- The current owner authorization covers only the v2 protocol/driver/addendum, one T1-A invocation, and a 525 s T1-A cap. That invocation plan is exhausted.
- The 112.094 s failed attempt and the 266.469 s two-cycle attempt are immutable charges. They cannot be refunded or reclassified.

A new protocol therefore needs an explicit, reviewed lineage mechanism. Monkey-patching `PROTOCOL_SHA256` or the checkpoint loader would bypass the frozen identity checks and would not produce an auditable driver/addendum/authorization chain.

## Proposed lineage mechanism

**Parent-binding acceptance**, implemented in a new driver, not in the frozen v2 driver.

1. The v3 protocol records the exact v2 parent binding (`1bf01d20…`) and the parent artifact hashes (protocol, driver, addendum, authorization, checkpoint, result, ledger).
2. The v3 driver accepts the v2 checkpoint only if:
   - the checkpoint SHA-256 is `3b1203b6…`;
   - `checkpoint.bindings` equals the recorded parent binding after canonical JSON normalization;
   - every scientific field equals the v3 binding: project, configuration, solver configuration, identity, mechanical loss, fuel, periodicity/cycle contracts, thresholds, exploratory workflow source, and all `motorsim.*` source hashes;
   - only `protocol_sha256` and `driver_sha256` differ, and both are bound separately in the v3 lineage block.
3. The v3 driver writes only new artifacts under `T1-A/v3/` and a new ledger `a3b-budget-ledger-v3.json`. All v2 artifacts stay byte-for-byte unchanged; their SHA-256 values are rechecked after every preflight/test.
4. The v3 ledger carries forward both parent T1-A entries: 112.094 s `FAILED_CLOSED` + 266.469 s `PARTIAL_BUDGET` = 378.563 s. It also carries 379.751 s as the conservative global wall. The rule is charge-as-is: no subtraction, refund, or retry credit.
5. The v3 run starts at `next_cycle=3`, invocation index 2, and runs exactly one cycle. It refuses to re-run cycles 1–2.
6. `freeze-atol-v3` and `analyze-v3` require the combined audited cycles 1–3. T1-A completion alone does **not** produce temporal/spatial sensitivity: T1-B..E remain unstarted.

Alternative considered: a derived dual-binding checkpoint carrying both parent and v3 bindings. It duplicates the parent snapshot/records and adds divergence risk; not recommended. A fresh T1-A trajectory is a fallback only if lineage cannot be implemented; it wastes the 378.563 s already charged.

## Budget options

Parent T1-A ledger: **378.563 s**. Frozen cycle-3 reservation: `144.55 × 1.10 + 5 = 164.005 s`. T1-B..E caps sum: **3670 s**. Global cap: **4320 s**.

| Option | T1-A cumulative cap | Available after 378.563 s | Buffer over 164.005 s | Total caps (with T1-B..E) | Global headroom | Status / consequence |
|---|---:|---:|---:|---:|---:|---|
| A | 525 s | 146.437 s | **−17.568 s** | 4195 s | 125 s | Infeasible under the frozen reservation; driver must refuse before cycle 3. |
| B | 560 s | 181.437 s | 17.432 s | 4230 s | 90 s | Arithmetic only, low margin; another partial is plausible if cycle 3 exceeds 181.437 s. |
| C | 600 s | 221.437 s | 57.432 s | 4270 s | 50 s | Feasible if authorized; smallest option with ≥50 s buffer and ≥50 s global headroom. |
| D | 620 s | 241.437 s | 77.432 s | 4290 s | 30 s | More per-config margin, less global headroom. |
| E | 650 s | 271.437 s | 107.432 s | 4320 s | **0 s** | Consumes the entire global cap-sum bound; not recommended. |
| F | no resume | — | — | — | — | Preserve PARTIAL; zero new spend; no convergence or predictive claim. Only zero-risk path. |

**Conditional recommendation (not a selection):** if the owner chooses to continue, option **C (600 s)** is the smallest scenario with at least 50 s above the frozen reservation and at least 50 s of global cap-sum headroom. Option B is arithmetic-only and should not be described as safe. Option E consumes all headroom. Option F is the only zero-risk path. The draft does not select a cap.

The total-cap column is a planning bound, not a prediction. Actual spend, the 600 s per-invocation cap and the 4320 s global deadline remain authoritative. Completing T1-A is necessary but not sufficient for temporal/spatial sensitivity; T1-B..E need separate authorization.

## What a new owner authorization would have to bind

At minimum:

- v3 protocol path and SHA-256;
- v3 driver LF-normalized SHA-256;
- v3 addendum SHA-256;
- parent protocol, driver, addendum, authorization, checkpoint, result and ledger SHA-256;
- `parent_cycles=[1,2]`, `start_cycle=3`, `invocation_index=2`;
- the chosen `t1a_cumulative_cap_seconds` (within 542.568–650.0 s);
- `global_cap_seconds=4320`, `per_invocation_cap_seconds=600`, `memory_limit_mib=3072`;
- `max_solver_invocations=1`, `no_retry=true`;
- carry-forward charges 112.094 s, 266.469 s, 378.563 s and 379.751 s;
- scope: T1-A cycle 3 only; no T1-B..E; no periodicity, steady-state, supported-resolution-domain or predictive claim;
- literal owner confirmation text quoting the hashes, cap and scope.

Hardening note: the v2 authorization records `memory_limit_mib=4096` while the protocol/driver enforce 3072 MiB. The v3 authorization should bind 3072 MiB explicitly, not copy the v2 4096 value.

## Verification before any execution

- Add v3 tests; no solver run.
- `lineage-preflight`: validate all hashes and the parent checkpoint without constructing the solver; expect PASS, zero steps.
- `preflight`: five configs PASS, zero solver steps.
- Negative tests: tamper each parent hash, one scientific binding field, the next_cycle, the cap bounds, and a v2 output path; expect REFUSED.
- Recheck SHA-256 of every v2 artifact after preflight/tests; require equality.
- `program_status.py check`.

## What this draft does not do

- Does not execute or resume the solver.
- Does not choose or freeze a cap.
- Does not freeze a v3 protocol, driver, addendum or authorization.
- Does not freeze `atol_obs`.
- Does not modify any v2 artifact or the owner decision record.
- Does not claim convergence, a supported resolution domain, periodicity, steady state or predictive capability.

## Key hashes

| Artifact | SHA-256 |
|---|---|
| v2 protocol | `c8ab07daeeccfaf00ee27c0bedbd4ddb25334384438b29e875d8ac04827c45ed` |
| v2 driver (LF) | `3062ed465f1a8d0e715ef9be07a4ddee4a0a1f11dba7cf4cf7824594e7b8bb42` |
| v2 addendum | `b93e743919f91486de166422d03ebe24e44702bfc40a7d355ddafa1054ba7d0b` |
| v2 authorization | `499986e1f74aeb1d35e77b087d0bb01d457ecc00f848e5868b87eeff8a4a0213` |
| T1-A checkpoint | `3b1203b6a1e4cb162910b8c011f4f562b693ee04f8f2801051f122416b11fcba` |
| T1-A result | `7124fbfe4929975ce68f4f94b1a67f89c267ad51372be81501098b23d6f85402` |
| v2 ledger | `12031ff8f7e0ca1f5be14854654e283773e0842c54e146f965d72f4c5108165e` |
| parent binding (canonical) | `1bf01d20acbc1e9f59aa36d4d933aa17c877b904a49a268c4d0d973f31d46e7e` |
| terminal receipt | `c57cb9c48fa51a4f93942320774a6cee87dd856eec855bbd6f0f31137ece358b` |
| budget/resume review | `fea88d133b150dc5cebf2be010d06b1afff241dd414505e46c7b38f1be02ff7d` |

## Next step

The owner selects an option (or rejects resume). If continuing: freeze the v3 protocol with the chosen cap, implement the v3 driver and tests, run `lineage-preflight` and zero-step `preflight`, write the v3 addendum, then request a separate explicit owner authorization. No solver until that authorization exists.

If stopping: preserve the PARTIAL result and checkpoint and close the objective with the existing no-convergence and no-predictive-claim limits.
