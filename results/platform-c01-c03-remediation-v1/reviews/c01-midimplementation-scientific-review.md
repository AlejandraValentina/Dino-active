# C01 mid-implementation scientific review

Review type: `INDEPENDENT_REVIEW`, read-only mid-implementation inspection. The writer was actively changing files, so this is actionable interim feedback, not acceptance of a frozen revision. Worktree HEAD at inspection was `18a10549df914cea4864870123d434c4c30c6f3d` plus uncommitted remediation. No tests or solver were executed; only bounded configuration/semantic probes of in-memory copies were used. No repository files or operative state were edited by the reviewer.

## Improvements observed

- Section-aware validation now rejects the original malformed-section, nonfinite/scalar-coercion and nested-unread-key classes before construction; fractional valve counts are no longer silently cast.
- The monitor property includes minimum complete cycles and validates the positive integer streak domain. Default numerical metrics and thresholds are preserved.
- Recorded histories are checked against actual numerical metrics and recorded tolerances, rather than trusting a stored passed flag. Zero-cycle incomplete results with null final-cycle data have a representable path.
- Summary/config binding now checks model choices, exact operating conditions, detector settings, provenance and native configuration identity.
- Signed finite friction coefficients remain possible; negative evaluated FMEP is ineligible rather than clamped.
- During this review, the writer added the native indicator identities previously requested. A probe changing only brake power to 999 or torque to 999 is now rejected when checked against config; boolean p_max is also rejected with config.
- The authentic stored A/B source summary/config positive control still returned an empty issue list. This does not imply the older unmanifested outer Desktop references are automatically eligible under C03's new provenance requirements.

## Remaining observed issues sent to the writer

1. `api.check_summary` without config accepted `operating_point=None`. The intrinsic native result contract should at least require a typed finite operating point, positive RPM and the documented equivalence-ratio domain even when its optional config preimage has not been supplied.
2. `code_commit=''` was accepted even with config when the historical summary lacked optional source_identity. Any declared commit should have a valid syntax. Unknown source origin can be retained historically and explicitly classified; it must not become reproducible just because its dirty flag is false.
3. `api.validate` on a configuration with finite `geometry.bore_mm=1e300` raised `OverflowError(34, 'Result too large')`. This is a finite but unbuildable numeric-domain input; catch expected construction overflow narrowly as structured CONFIG_INVALID. A catch-all masking internal implementation defects would be inappropriate.
4. The source manifest's required dependency anchors should include newly critical validation/artifact-verification modules. Otherwise an internally rehashed manifest omitting the implementation that decides eligibility could still satisfy the old anchor list. The existing digest validator correctly checks consistency, but an unsigned manifest is not proof of maliciously forged ancestry; retain that stated limit.

No historical source result was altered by these probes. The operator-facing behavior on unavailable/invalid historical records must preserve their raw bytes and expose issues, not silently repair their metadata.

## Conservation assurance decision

The exact `<1e-12` maximum mass/energy/elements closure bound appears in frozen native regression tests at `tests/test_dino4t_engine.py:44`, `tests/test_dino4t_stage2.py:132` and `:193` (with additional vessel checks nearby). It is reasonable to reuse it prospectively as an explicitly **versioned result-assurance eligibility profile** in the authorized remediation. A gross closure of 1.0 can then be retained but marked `INELIGIBLE_INTEGRITY`.

The limit must not be presented as an already established universal V1 numerical/physical guarantee for every operating condition and run length: the original tests apply to their own fixtures, and roundoff accumulation can depend on state and duration. Record the exact criterion, native-test sources, profile and scope; preserve raw numerical values/status and the scientific detector. If claiming exact reuse, preserve the strict `<1e-12` comparator. This is not a predictive error threshold, evidence of physical correctness or permission to adjust tolerances after observing results.

## Historical comparison identity clarification

The original V1 comparison receipt and comparison_id must remain unchanged. A new V2 comparison can legitimately have a different ID because it adds original artifact/run manifest identities and versions its digest preimage. Do not force the V2 digest to equal the historical ID. Positive compatibility means preserving the authentic source-result bytes/identity and explicit receipt-backed reconstruction, not fabricating unchanged hashes across a versioned schema change.
