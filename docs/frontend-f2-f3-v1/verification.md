# Verification ledger (in progress)

- Consolidation: main fast-forwardf97469b→97e40bd; rc13 ZIP SHA256 unchanged. receipt: results/frontend-f2-f3-v1/consolidation.json.
- Initial interactions:17PASS. Added overlay qualification check caught omitted synthetic-origin presentation; origin metadata is now explicit. Job application test corrected its expected terminal state after an explicit shutdown cancellation.
- Jobs/interactions final:16PASS. Covers real application command routes plus synthetic executor lifecycle doubles; these tests are not physical validation.
- Combined first run:95 progress dots, then600s timeout with a shared recovery root. Not accepted. Isolated recovery roots per test are required; diagnose/re-run before source closure.
- Source application, protected regressions and grouped clean Windows candidate remain pending. No SOURCE_ACCEPTED/WINDOWS_ACCEPTED claim for F2/F3 yet.


Follow-up: the combined run reached CP2 then waited on recovery selection. Faulthandler identified _offer_recoveries inside CP2 cleanup. The new module fixture had leaked DINO_RECOVERY_ROOT across tests; it now uses a scoped MonkeyPatch and restores both roots. No product recovery behavior or scientific criterion was relaxed.

Extended source application found a cursor assertion while a requested result reload remained active. The harness now waits for completion; result readers also bind callbacks to request generations so an earlier background import cannot replace a newer selection. Ordering has an explicit negative regression. Real queued2T/native executions, pending and active cancellation, persistence and reference binding passed before this assertion; the overall run remains FAIL until the complete rerun passes.
