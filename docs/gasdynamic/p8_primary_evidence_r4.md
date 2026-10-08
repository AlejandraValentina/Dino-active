# P8 durable primary evidence and offline audit (trajectory binding)

P8 summaries are no longer the authority for replay/accounting acceptance. Each
anchor writes two compressed artifacts, one per deterministic execution:
`primary-<rpm>-first.json.gz` and `primary-<rpm>-second.json.gz`. The anchor
summaries record their schema, relative path, compressed byte length and
SHA-256. Earlier campaigns remain unchanged; trajectory binding uses a new
campaign directory and the `P8_PRIMARY_ANCHOR_V2` schema.

## Evidence classes

- **PRIMARY:** each per-run artifact. It contains the terminal conservative and
  four-species state, initial and external ledgers, P7 event ledger and source,
  raw SSPRK2 gas history, both accepted-stage work rates/states, accepted `dt`
  and CFL samples, resolved interface donor/fraction traces, resolved external
  gas boundary fluxes, and actual before/after four-species deltas accepted by
  the intake/exhaust boundary routine. It also records the in-event checkpoint
  state plus restart terminal state. Every accepted measured step additionally
  stores its post-step coupled endpoint: gas conservative state, cellwise four-
  species inventory, external and accumulated gas/P7 ledgers, source, fresh
  delivery, short circuit, angle, cycle identity and accumulated accepted time.
  The gas SSPRK2 record stores its raw `q_n` candidate; the accepted endpoint
  snapshot is taken immediately after `system.step` installs that candidate
  and completes P6/P7 stage work. Chamber primitive install/reconstruction may
  differ from raw `q_n` by one binary64 ulp, so the post-install snapshot and
  per-step totals are the canonical exact accepted state. The campaign configuration is stored
  beside the terminal record.
- **DERIVED:** the offline auditor's values reconstructed from PRIMARY: fresh
  delivery and short circuit by integrating signed donor-resolved fresh-species
  interface fluxes with the SSPRK2 half-step weights; indicated work, power,
  torque and peak pressure from raw step/stage records; heat, mass/energy
  residuals from raw history and external boundary fluxes; species-total
  residual; and terminal replay digest.
- **SUMMARY:** the consolidated JSON and per-anchor JSON. Their values are
  compared with DERIVED and their cross-copy equality is only a secondary
  integrity check.
- **DIAGNOSTIC:** CSV. It is checked against summaries after those summaries
  have been accepted against PRIMARY; it is never an authority for a scientific
  value.

## Terminal replay digest

The preimage is the complete `terminal` object in `P8_PRIMARY_ANCHOR_V2`, after
the offline auditor independently reconstructs and substitutes these four
counters: `fresh_delivered`, `fresh_delivered_tr1`, `fresh_delivered_tr2`, and
`fresh_short_circuit`. The remaining exact fields are terminal angle,
conservative state, species masses/initial/external, gas external cumulative
and last exchange, gas accumulated ledger, gas initial/previous totals, P7
events and ledgers, P7 source delta/enabled/angular rate, raw verification,
gas external-flux and accepted species-boundary traces, selected numeric gas
history, and accepted `dt`/CFL
samples, including the accepted endpoint-bearing history. Before building the
preimage, the offline auditor checks every accepted step's identity, dt, CFL,
angle and elapsed time, and compares the final post-install endpoint exactly
against terminal gas,
species, external state, cumulative ledgers, P7 source/ledger, delivery and
short-circuit fields. It also requires terminal totals to equal the final raw
history totals. Only after that history-to-terminal binding does it rebuild
the canonical digest. A correct digest for a coherently altered terminal and
restart cannot substitute for a match to the persisted trajectory.

Canonical bytes are UTF-8 JSON with lexicographically sorted object keys,
compact `,`/`:` separators, ordered arrays, decimal JSON integers, and Python's
shortest round-trip binary64 JSON representation. Field presence is exact;
`-0.0` and `0.0` remain distinct. NaN, positive/negative infinity, non-string
object keys, booleans in numeric fields, and unsupported values are rejected.
The digest is lowercase SHA-256 over those bytes. The offline audit implements
this encoding itself and does not import the producer's digest function.

The independent replay gate validates each run's history-to-terminal binding,
compares both recomputed preimages and terminal state objects directly,
compares the persisted restart terminal state directly to the validated
uninterrupted terminal state, then checks the independently rebuilt digests
and finally compares DERIVED values against JSON/CSV. A stored PASS,
stored digest or matching pair of summaries cannot substitute for these
comparisons.

The gzip SHA-256 detects file corruption against its current references; it is
not a signature or an authenticity guarantee because the artifacts and their
references are local files. The P8 contract requires independent recomputation,
not a new signing infrastructure. No physics, solver, scientific threshold,
anchor RPM, or conditional/experimental claim changes here.

Audit command:

```powershell
.\.venv\Scripts\python.exe -m dev_orchestrator.p8_durable_audit `
  results/p8-wide-rpm-trajectory-bound-20260930 `
  --output results/p8-wide-rpm-trajectory-bound-20260930/primary-audit.json
```
