# Verification ledger (in progress)

- Consolidation: main fast-forwardf97469b→97e40bd; rc13 ZIP SHA256 unchanged. receipt: results/frontend-f2-f3-v1/consolidation.json.
- Initial interactions:17PASS. Added overlay qualification check caught omitted synthetic-origin presentation; origin metadata is now explicit. Job application test corrected its expected terminal state after an explicit shutdown cancellation.
- Jobs/interactions final:16PASS. Covers real application command routes plus synthetic executor lifecycle doubles; these tests are not physical validation.
- Combined first run:95 progress dots, then600s timeout with a shared recovery root. Not accepted. Isolated recovery roots per test are required; diagnose/re-run before source closure.
- Source application, protected regressions and grouped clean Windows candidate remain pending. No SOURCE_ACCEPTED/WINDOWS_ACCEPTED claim for F2/F3 yet.


Follow-up: the combined run reached CP2 then waited on recovery selection. Faulthandler identified _offer_recoveries inside CP2 cleanup. The new module fixture had leaked DINO_RECOVERY_ROOT across tests; it now uses a scoped MonkeyPatch and restores both roots. No product recovery behavior or scientific criterion was relaxed.

Extended source application found a cursor assertion while a requested result reload remained active. The harness now waits for completion; result readers also bind callbacks to request generations so an earlier background import cannot replace a newer selection. Ordering has an explicit negative regression. Real queued2T/native executions, pending and active cancellation, persistence and reference binding passed before this assertion; the overall run remains FAIL until the complete rerun passes.


Clean implementationd4fc244:47base +76extended real Windows Qt source checks PASS, with independent owned-process termination receipts. Extended workflows cover serial real2T/native queued jobs, active/pending cancellation, preserved classification, actual0D execution, eligible synthetic pressure overlay, mouse pan, keyboard cursor/zoom, expanded views, export, actual980x680/1280x720 dimensions, recovery preview/defer/SaveAs cancellation and reopen. Recovery reopens the correctly seeded renamed project; queue ownership releases and reacquires on restart. Source product reports no packaged identity; revision is bound by clean Git and product tree hashes, not inferred from the About dialog.

Combined source120PASS; subsequent targeted39PASS and24PASS overlap those regressions and cover later presentation/recovery changes. Protected301PASS+3SKIP,4inherited NumPy warnings. These counts are not summed into unique tests. The first timed-out/failed attempts remain preserved and are not acceptance evidence.

Evidence-only commits afterd4fc244 may precede packaging: motorsim/ and packaging/ Git tree IDs must remain identical. The Windows build and actual frozen receipts bind the candidate revision explicitly.


Final capture review found a reference0D autosave collision: RecoveryController read dict identifiers only, but FourStrokeContext.project is a dataclass. Distinct references therefore shared4T0D-proyecto.json. Corrected identity from the public name and introduced a reference-onlyV2 filename key with a digest of the exact name so Windows sanitization cannot merge different names. LegacyV1 entries stay readable and unmodified; the selector derives their human name from serialized project data. Tests cover distinct names, colliding sanitized names, independent clear and legacy preview. This is an application-storage fix, not a scientific schema change.

The first rc14-552a5673 passed47base,76F2/F3,14CP1,8CP2 and12externalUIA checks. It is preserved as a superseded candidate because those checks did not cover multiple reference-project drafts. The corrected candidate must pass the added application case and repeat Windows acceptance; no old binary or receipt is rewritten.
