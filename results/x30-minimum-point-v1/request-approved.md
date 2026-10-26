# X30 Senior data request — owner-approved, not sent

**Status:** `OWNER-APPROVED FOR DELIVERY — 2026-10-26`
**Delivery status:** `APPROVED_NOT_SENT`
**Delivery channel:** external owner mail client. The agent has no email tool and does not claim delivery.

## Recipients

- Fernando Ortenzi <fernando.ortenzi@enea.it>
- Andrea Bossaglia <a.bossaglia@iamekarting.com>

## Subject

X30 Senior — remaining geometric input for a 1D comparison

## Body

The exact plain-text body is in [`request-body.txt`](request-body.txt). Copy it without the markdown heading.

## Minimal data requested

1. Assembled pre-compression crankcase free gas volume at a specified crank angle, or an equivalent primary compression ratio.
2. The boundary definition: does the value include inlet and/or transfer passages? State the sealing plane.
3. If readily available: representative transfer passage lengths/sections and whether the manual's 10.15 cm3 chamber volume includes the checking insert.
4. Optional: any shareable numerical X30 Senior data underlying Figure 10 and the corresponding operating conditions.

## Evidence and provenance

- [Decision B and source reconciliation](../x30-public-reconstruction-v1/decision.md)
- [Refined draft](../x30-public-reconstruction-v1/email-draft-refined.md)
- [Technical inventory V2](../x30-public-reconstruction-v1/x30-technical-inputs-v2.json)

SHA-256:

- `CB3F8601B39A76A6460C128A6C957DDF3860E9D84630D97C9985482938DD098A` — decision.md
- `693B21FA2842700B70C11849B699759E138CEFB0142A24912EA7E9EC7BEACBD8` — email-draft-refined.md
- `76CBD1A8B01EEB9E045C6BFBD9107427F2FCB9CA09F341489B6A13D0577C46FD` — x30-technical-inputs-v2.json

## After sending

Record the delivery date and any reply in `receipt.json`; do not change `delivery_status` to `SENT` without owner confirmation. When a reply arrives, create `input-intake.json` with the volume, crank angle, boundary definition, source and uncertainty before any configuration work.
