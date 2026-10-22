# Single periodic-point execution

This executor is limited to the independently prepared 3000 RPM reference point.
It does not authorize a scientific run and does not resume A3b or the standalone
representative-cycle snapshot. Start conditions are independent. Existing
scientific models, geometry, 48 cells, CFL 0.4 and detector thresholds apply.

## Existing components and continuity

`scripts/diagnostics/periodic_point_executor.py` coordinates the existing
`run_exploratory` workflow and the already tested bounded subprocess supervisor.
It does not implement another engine, detector, primary format or serializer.
The workflow now accepts optional admission/completion callbacks at committed
cycle boundaries. Defaults preserve ordinary callers.

The existing checkpoint envelope is unchanged. On resume, every committed
primary is independently replayed. The detector is reconstructed from those
audited observables; every recorded update and the complete checkpoint detector
snapshot must match. Invalid hashes, incompatible identities, missing/duplicate
cycles and orphan primaries remain fail-closed. No standalone checkpoint is
silently converted to a workflow checkpoint.

Scientific source hashes and configuration are recorded separately from the
workflow/executor/supervisor hashes. Both groups remain exact requirements;
separating them does not create a hash-validation exception. Only the workflow
source changed from the representative trial; physical solver modules and the
detector remain unchanged.

## Preparation and authorization

Use a new external directory as `--root`. `prepare` performs zero solver steps:

```powershell
python scripts/diagnostics/periodic_point_executor.py prepare --root $pointRoot
python scripts/diagnostics/periodic_point_executor.py verify --root $pointRoot
```

Preparation writes the immutable execution definition, document and zero-charge
ledger. It does not create an execution authorization. After independent owner
approval, the authorization JSON must contain exactly:

```json
{"authorized": true, "definition_sha256": "SHA256_FROM_VERIFY"}
```

Only then may the single experiment be launched with:

```powershell
python scripts/agents/run_logged.py --name periodic-point --out $logRoot --timeout 3010 -- python scripts/diagnostics/periodic_point_executor.py run --root $pointRoot --authorization $authorizationPath
```

The outer logger timeout is an emergency process wrapper, not an extension of
the scientific budget. The executor limits accumulated charged time to 3000 s
and each invocation to 600 s. It stops earlier for periodicity, ten completed
cycles, insufficient remaining budget or a terminal failure. No scientific
execution is performed by this implementation/preparation intervention.

## Budget and interruption

Before each spawn, the entire invocation allowance is durably reserved. The
worker has a smaller deadline; the supervisor stops it ten seconds before the
outer invocation cap. A further closure reserve is conservatively charged.
Startup, resume audits, stepping, primary production, persistence and supervisor
closure are included. RAM guards require 4096 MiB free, 3072 MiB maximum worker
RSS and 4096 MiB for the monitored supervisor/worker process tree. RSS is sampled,
not an OS hard allocation ceiling. The lightweight logging wrapper is excluded
from that monitored tree.

Cycle admission uses measured completed-cycle cost with a safety margin; this
is a scheduling estimate, not a numerical tolerance or a guarantee of convergence.
The external supervisor is authoritative if cost grows unexpectedly. A normal
boundary yield can continue in the next invocation with the same identity and
checkpoint. Full historical reaudit costs count against each invocation; the
executor may consequently stop before ten cycles. The existing 512 MiB workflow
artifact cap is preserved and also can produce a resource-limited result.

An abrupt process/supervisor failure is terminal, not an automatic retry. The
last manifest selects the last complete checkpoint. Partial/orphan evidence is
preserved and never adopted automatically. `recover --root ...` is zero-step:
it rejects live owners and settles an abandoned invocation at its full reserved
charge. It does not clear terminal state, remove locks, fabricate missing cycle
history or authorize further execution. Evidence can therefore be inspected
without resetting consumption. Worker exceptions are operational fail-closed
errors unless the workflow actually records a scientific failure.

## Scientific interpretation

Existing engineering output rules decide whether IMEP, FMEP, BMEP, power and
torque are defined. Accepted detector classification alone cannot turn missing
engineering values into valid outputs. Period-2 remains period-2; it is never
converted into period-1. No spatial independence or experimental prediction is
claimed by this executor.
