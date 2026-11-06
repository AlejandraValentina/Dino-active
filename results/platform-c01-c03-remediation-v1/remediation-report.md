# C01/C03 remediation — source-level acceptance

Branch: `fix/dino-c01-c03-v1`, isolated from the operative worktree.
Acceptance/preregistration: `18a10549df914cea4864870123d434c4c30c6f3d`.
Implementation/source freeze: `0f81453598a2d047f908103c56fb462ef5f46221`.
No merge, push, Windows build, distribution or scientific campaign.

## Finding dispositions

| Finding | Root cause and correction | Evidence / remaining qualification |
|---|---|---|
| F01 | Invalid detector domains and disagreement between `status` and actual minimum-cycle decision. Typed positive counts/finite tolerances and one shared decision now reject false periodic success. Original valid thresholds and comparisons preserved. | Pre-fix failures and adversarial detector/history tests; independent C01 review. Periodicity remains numerical, not measured validation. |
| F02 | Summary-only shape checks did not bind actual configuration, cycle history, models or indicator identities. V2 assessment validates all of these, evaluated losses and explicit roundoff admission. Raw incompatible results are retained as ineligible. | Genuine A/B summaries remain semantically valid. Mutated cycles, gross closure, identities, selectors, RPM and indicators fail. Signed friction coefficients are not blanket-banned. |
| F04 | Example-derived allowlist, coercion and inconsistent error boundary. Declarative section-aware typed schema, strict JSON and structured construction/arithmetic errors; actual-default discovery. | Invalid fractions/bools/nonfinite/nested keys/objects/unknown models and extreme finite arithmetic are rejected without solver. No arbitrary RPM cap or calibration policy. |
| F06 | A summary hash and nearby mutable paths did not bind original trace/config/metadata. Producer manifest → immutable run metadata → supplied original outer reference; immutable verified plotting snapshot and action-time revalidation. | Replacement trace, rehashed inner manifest, redirected metadata and stale exports rejected. Manifestless history retained as LEGACY_UNVERIFIED; no trusted curve/A/B promotion. |
| F08 | Spec, manifest and clean guard maintained different input sets. One shared declaration binds mandatory native example, application/static inputs, optional external examples/data and build-license preimages. Copy and before/after snapshot guards. | Changed/deleted/untracked native/shared/static/dynamic inputs fail. Source/infrastructure verified only; no new Windows candidate or byte-identical third-party EXE claim. |
| F09 | `code_dirty` inspected native files but omitted shared runtime dependencies. Complete application/shared source/data preimage inventory, Git-policy identity, capture stability and unknown/incomplete fallback. Packaged identity requires actual shipped preimages. | Shared kinematics, ignored runtime, missing Git, source race and package mismatch tests. Runtime Python/NumPy/SciPy/platform versions are retained; third-party binaries are not fully archived or byte-attested here. |
| F12 | Absolute-path dependence and implicit EOL changes obscured raw-byte authority. Portable original references/bundles, explicit byte policies, canonical safe paths/no-overwrite publication and opt-in recorded-EOL receipt reconstruction. | Original paths can disappear after relocation without changing new comparison identity. Original summary/trace raw SHA versus original config canonical identity remain distinct. No historical raw bytes/hash rewrite. |
| F13 | Static build/default labels confused legacy/native and actual selected models. Separate metadata and resolved model selection including disabled heat/burn, order and restriction. | Actual constructor defaults and retained legacy Wiebe-family label distinguished from zone selector; actual `result.models` checked against config. No model promotion. |

## Verification interpretation

Failing-before native probes: ten failures. Provenance-boundary probes: three
meaningful failures. These are retained unchanged in `native-baseline/` and
`provenance-baseline/`. Intermediate unsuccessful development runs remain in
`verification/` and `provenance-verification/`; they are not deleted or replaced.

The first expanded run had 166 passes and 17 failures. Most failures exposed
nonprotected application fixtures relying on synthetic, unbound in-memory
endpoints or legacy clean flags. Those fixtures now publish self-consistent
original-byte bundles in a temporary synthetic Git repository, with explicit
SYNTHETIC_PRESENTATION_FIXTURE origin. Unknown-key expectations now require
invalidity; sparse legacy build flags now require unknown source identity.
Negative tests remain fail-closed. No frozen scientific expected values changed.
Two results also correctly detected source changes while implementation was
still in progress. Final verification pins a clean implementation commit and
retains both observations rather than attributing them to the historical 115.

Independent scientific and integration reviews, including negative probes,
closed their intermediate findings at exact source hashes. They did not execute
solver campaigns or Windows builds. Their scope is source/infrastructure, not
whole-platform release or physical validity. See `reviews/` and source-freeze
receipt for the original-byte copies and commit correspondence.

## Residual boundaries

- C02/F03 phase-safe continuation and other audit findings remain outside scope.
  A caller must not treat the existing opaque initial state as an exact restart.
- B1.2, operative status and OpenSpec remain owned by the parallel development;
  no changes from that worktree were incorporated. Adoption interface is
  `docs/c01-c03-native-integration-contract-v2.md`.
- Historical data lacking original producer bindings/source inventories remain
  explicitly qualified. Receipt reconstruction cannot retroactively prove old
  clean source, original raw config bytes or experimental validity.
- Runtime dependency versions and pinned build requirements are recorded, but
  complete raw third-party binary attestation is not established. Future build
  content/EXE acceptance is separate; no existing candidate is reclassified.
- Protected P4–P8 tests require their recorded external/relative artifact context.
  Missing optional historical data/skips are disclosed, never treated as passes.
- There is no new measured validation, predictive claim, steady-state campaign,
  performance campaign, scientific tolerance change or physical-kernel change.

Final invocation results are recorded in `verification/final-verdict.json`.
Counts denote regression/contract checks, not independent physical experiments.


## Recorded outcome

C01: **PASS_SOURCE_SCOPED**. C03: **PASS_SOURCE_INFRASTRUCTURE_SCOPED**.
The eight causes are corrected at the source/application boundary and independently
reviewed. This is not a new product/release acceptance or experimental validation.

- Fixed-source expanded native/source/provenance suite: **187 PASS, 2 FAIL**.
  The two failures were assertion/fixture integration defects, not ignored: the
  unknown-key assertion now checks both structured issue paths rather than the
  order of the first message; the transient comparison now uses genuinely bound
  references instead of pathless mocks. Both rechecked **2 PASS**, including an
  actual bounded native cycle. Production source did not change. We do not
  misreport the earlier expanded invocation as a single all-green run.
- Protected P4–P8: **301 PASS, 3 SKIP, 4 existing NumPy deprecation warnings** in
  the explicit external/relative historical artifact context. The three skipped
  optional historical-data checks remain disclosed; no contracts/tests altered.
- Project/report/legacy 2T/4T compatibility: **47 PASS**.
- Full broad offscreen Desktop attempt: native Windows access violation
  `0xC0000005`; earlier broad attempts also reached their finite 180s/90s caps.
  Exact same seven-test prefix, including the bounded custom-engine A/B test,
  then passed on audited baseline353e3f0 (**7 PASS**,139.25s) and corrected
  source (**7 PASS**,139.30s), with the same diagnostic flags. This does not
  establish the cause or turn the crashed whole28 invocation into PASS.
  A general Desktop verification issue remains open; no release readiness claim.
- Genuine new native producer bundle from the successful one-cycle regression
  is retained byte-for-byte under verification/native-producer-smoke. Its
  supplied original outer reference reopens VERIFIED with complete clean source
  identity at0f81453 and NOT_CONVERGED. Verification reuses those bytes and
  executes neither solver.
- Actual source/recipe preflight: clean application closure194 preimages;
  shared explicit recipe263 inputs, including mandatory native example. No
  build. Frozen P9 Git-blob SHA remains79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d.

Remaining follow-up is the isolated Windows/offscreen crash diagnosis before
claiming a fully green Desktop regression, downstream B1.2 contract adoption,
and a separately authorized package acceptance. No old scientific campaign is
reactivated. All unsuccessful attempts and the independent findings are retained.
