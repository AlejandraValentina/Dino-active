# C01 final independent scientific review

**Disposition: PASS, scoped to the reviewed C01 configuration/result/detector remediation source and the explicit assurance profile.** This is not scientific validation of Dino, closure of C03, Windows acceptance, or authorization to activate another stage.

**Review classification:** `INDEPENDENT_REVIEW`, read-only, distinct from the implementer. Date: 2026-11-06, America/Montevideo.

## Reviewed identity and limits

The remediation worktree was based at HEAD `18a10549df914cea4864870123d434c4c30c6f3d` with uncommitted production changes. The review is bound to the exact raw file hashes below, rather than falsely attributing those changes to that HEAD. The final independent probes observed stable hashes before and after their execution. Any later changes require review of the changed scope; the eventual commit should be checked against these preimages.

| Reviewed source | SHA-256 |
|---|---|
| `motorsim/dino4t/validation.py` | `b04342a84ec12fdb8ad48728f9f80721796836284e695ebcc7564d84559e71a6` |
| `motorsim/dino4t/config.py` | `c70afbf9c98838e5be43ded509f6b30c829a0242c47b531b116911a57d3f7551` |
| `motorsim/dino4t/api.py` | `860c87f4c14c1f1775ff211e1b4a4a474906e0564b834bb4fb1fd861d14a9f04` |
| `motorsim/dino4t/cycle_analysis.py` | `54763afaabf42d1067079f25e274a6f7e96a9e33f8c0192b226a17e5a6d60470` |
| `motorsim/dino4t/runner.py` | `9cad0f94505ca45fcee865289cac00723a46041ac2ccc8b2fc34278bfd7847e8` |

Assurance profile document SHA-256: `d86a3662dab1fe5b57e3518461203900e311d21eaf24cffe29a01b1b759ca235`.

Independent probe source: `c01-final-probes.py`, SHA-256 `a23735991b48b6ce7c1ecf13fea09547f0208485a346b78692473bbe63b24666`.

Independent probe observations: `c01-final-probes.json`, SHA-256 `72cc7a671a6ff6f171b781485812ae1fadebaf892407c08cb6d2351b96928c37`.

The writer reported 43 targeted passing tests. This reviewer did not accept by that count or rerun that suite. The independent review used source inspection and its own bounded, reproducible contract probes. No solver integration, periodicity campaign, GCI campaign or new A/B pair was executed. The probes explicitly record `solver_runs=0`; invalid-option tests replace the runner with a sentinel that would fail if computation were attempted.

## Root-cause correction verified

1. **Typed and section-aware input admission.** Bool/fractional valve counts, nonfinite consumed coefficients, malformed sections, nested unread controls and misplaced otherwise-known names are rejected before calculation. The valve-count truncation was removed; existing genuine integer counts retain their values. Unknown combustion model text is no longer accepted as a silent new selector. The original `combustion.model=WIEBE_SINGLE_ZONE_V1` is a preserved legacy marker alongside the actual `zone_model`; it should be documented as compatibility metadata rather than the operative selector.
2. **Periodic classification is the detector's full decision.** The monitor property and convergence return now include minimum complete cycles as well as a passing streak. A positive integer count is required, so the original zero-streak false success cannot be reached by an accepted config. The independent monitor fixture observed NOT_CONVERGED after one and two cycles with a one-transition requirement and minimum three cycles, followed by PERIODIC_CONVERGED only after the third. The original metric equations, default tolerances, default minimum cycles and inclusive boundary comparison remain intact for valid inputs.
3. **Semantic result/config binding.** Authentic stored A/B source summaries and resolved configs remain accepted without mutation. Counterfactual changes to power, torque, operative metadata, a passed flag or unauthenticated validation claims become issues. The validator binds RPM/equivalence ratio, model selections, detector settings, provenance, configuration identity and native work/loss/power/torque conventions. This prevents two agreeing but incorrect summaries from establishing eligibility solely through matching each other.
4. **Expected malformed/domain inputs stay structured.** The previously exposed finite-geometry construction overflow is CONFIG_INVALID. A separate final-review probe exposed overflow in derived indicator arithmetic at finite RPM `1e300`; the final source returns a semantic issue rather than raising. The correction catches arithmetic domain errors narrowly rather than replacing internal programming failures wholesale with input errors.
5. **Valid partial evidence stays representable.** A zero-cycle incomplete record with null final performance and an empty comparison history remains a valid informative partial. A completed/periodic claim cannot be inferred from it. Semantic checks did not rewrite any probe input. Historical malformed records must continue to retain original bytes and expose ineligibility, rather than being silently normalized.
6. **Loss guard preserves the equation.** Signed finite Chen-Flynn coefficients are not universally banned. The independent counterfactual postprocessing fixtures accepted a negative coefficient yielding positive evaluated FMEP and accepted zero FMEP; they rejected negative evaluated FMEP. There is no clamp or recalculation of stored evidence. The tests are contract fixtures, not new simulated engine evidence or a validation of the correlation.

## Explicit roundoff assurance profile

`DINO4T_ROUNDOFF_ASSURANCE_PROFILE_V1` is documented prospectively and preserves the exact strict `<1e-12` mass/energy/element maximum closure comparator from frozen native engine/Stage-2 regression fixtures. It is described correctly as an application admission profile for its native engineering assurance scope, not a universal historical V1 guarantee or predictive accuracy target.

The independent boundary probes accepted a maximum immediately below `1e-12`, rejected equality at `1e-12`, and rejected gross closure 1.0. The raw status, metrics and history were not changed. Outside-profile records remain retained but ineligible for trusted integrity admission. A different justified scope requires another recorded profile; the current bound must not be retuned after a desired result is seen.

## Numerical and historical preservation

Inspection of the diff against frozen audit source `353e3f04ca17c59c660ca5b5269a5b9a1755d0b1` showed no changes in native engine, duct, closures, restriction, combustion or two-zone equations, nor the protected existing engine/Stage-2 test files. Existing canonical config hashes for valid finite inputs are preserved by validation; the authentic A/B source artifacts remain positive controls. This review does not replace the broader physical regression obligations with source inspection.

The new V2 artifact/comparison contracts may legitimately have a new comparison ID because they include new original-manifest identities. The original V1 comparison receipt and ID must remain unchanged historical evidence; no digest definition should be changed to force old and new IDs to match.

## Findings raised during this final pass

The initial final-pass probes found two residual issues: arbitrary `combustion.model` text was accepted, and extreme finite derived arithmetic raised OverflowError. The implementer corrected both while the review was in progress. The final independent probes confirm their rejection/structured issue behavior. The intermediate scientific review and probe history remain separate artifacts; they are not replaced by a test-count approval.

No blocking C01 issue remained in the reviewed behaviors and preimages. This is a bounded review, not proof that every possible Python object or future schema extension has been explored. C03 provenance/package review remains independent, and no unbuilt Windows executable is accepted here. Unsafe exact continuation, additional model verification, measured calibration/validation and predictive claims remain outside C01 and retain their previously recorded limitations.
