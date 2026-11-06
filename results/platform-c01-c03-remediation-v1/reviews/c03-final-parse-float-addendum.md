# C03 final review addendum — finite JSON float parsing

Reviewer: `/root/integration_review`, independent read-only reviewer.
Decision: **PASS — narrow parse_float delta**.
Final source freeze: `0f81453598a2d047f908103c56fb462ef5f46221` on the remediation branch; this does not imply integration into main or a new Windows build.

This addendum supplements and does not overwrite `c03-final-review.md`. It explicitly inspects the finite `parse_float` callback in `motorsim/dino4t/artifacts.py` and its adversarial regression. No general audit or solver run is repeated.

## Inspected behavior

`parse_json` supplies `json.loads` with a callback that first converts a JSON decimal/exponent token to the existing Python float type and then rejects a nonfinite result. This closes the standard-parser behavior in which syntactically legal `1e999` becomes positive infinity without invoking `parse_constant`. The pre-existing duplicate-key, explicit NaN/Infinity token and object-root checks remain.

The callback does not round finite numbers beyond normal float parsing or modify solver equations, output values, tolerance policy or artifact hashing. A rejected overflow is an expected malformed artifact, surfaced as ValueError at the reusable boundary.

## Independently observed narrow probes

- `1e999`, `-1e999`, and nested `[1,1e999]`: controlled ValueError, nonfinite JSON number.
- `NaN`: controlled ValueError through the existing parse_constant guard.
- Ordinary `3.141592653589793`, finite `1e308`, string `"1e999"`: same parsed values as the prior ordinary JSON float behavior.
- `-0.0`: negative-zero sign retained.
- Solver integrations and builds: zero.

Observations are retained in `c03-parse-float-addendum-probes.json`, SHA-256 `220c3fc754dfff052d398265b765c7aca9c68bf242e6cabf6de1394e93d12847`.

## Final identity reconciliation

All fifteen source/test hashes listed in the original `c03-final-review.md` match the frozen current worktree. The parse_float edit had therefore already landed by that report's final byte-hash capture, although this addendum supplies the explicit semantic review of it. There is no unreviewed byte-hash discrepancy to conceal or reinterpret.

- `motorsim/dino4t/artifacts.py` SHA-256 `f701109823b150728a8a3f40507fe5c966b2de638318c89dbdccd3e8d94d0f91`.
- `tests/test_c01_c03_artifact_binding.py` SHA-256 `0870b6e7d152bdb834077dda45a0133336c064b5d205913cf76c2f403c51b232`.

The earlier scoped C03 source/infrastructure PASS remains. The enlarged final regression result, any separately authorized Windows verification, the other scientific review scopes and final acceptance bookkeeping remain distinct; this addendum does not declare those checks passed. The original reviews and failed development logs remain preserved.
