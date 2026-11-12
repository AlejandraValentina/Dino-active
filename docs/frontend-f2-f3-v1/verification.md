# Verification ledger (in progress)

- Consolidation: main fast-forwardf97469b→97e40bd; rc13 ZIP SHA256 unchanged. receipt: results/frontend-f2-f3-v1/consolidation.json.
- Initial interactions:17PASS. Added overlay qualification check caught omitted synthetic-origin presentation; origin metadata is now explicit. Job application test corrected its expected terminal state after an explicit shutdown cancellation.
- Jobs/interactions final:16PASS. Covers real application command routes plus synthetic executor lifecycle doubles; these tests are not physical validation.
- Combined first run:95 progress dots, then600s timeout with a shared recovery root. Not accepted. Isolated recovery roots per test are required; diagnose/re-run before source closure.
- Source application, protected regressions and grouped clean Windows candidate remain pending. No SOURCE_ACCEPTED/WINDOWS_ACCEPTED claim for F2/F3 yet.
