# Derived task view

- [x] X30M-REQUEST-PACKAGE: owner authorization recorded; send-ready request and receipt prepared, delivery external. — verificar: file:results/x30-minimum-point-v1/request-approved.md contiene "OWNER-APPROVED"
- [x] X30M-VOLUME-PROCEDURE: boundary-explicit volumetric measurement procedure prepared as local fallback; no measurement executed. — verificar: file:results/x30-minimum-point-v1/volume-measurement-procedure.md contiene "boundary"
- [ ] X30M-OWNER-SEND: owner sends the approved request from an external mail client and records confirmation. — verificar: file:results/x30-minimum-point-v1/receipt.json contiene "SENT"
- [ ] X30M-INPUTS: accept a single precompression volume with crank angle and inlet/transfer boundary definition; reject borrowed ratios. — verificar: file:results/x30-minimum-point-v1/input-intake.json contiene "precompression_volume_cm3"
- [ ] X30M-CONFIG-FREEZE: freeze one revision-coherent X30 configuration with explicit assumptions after inputs arrive. — verificar: file:configs/reference_cases/x30_senior_v1.json contiene "precompression"
- [ ] X30M-POINT-EXEC: preregister limits and run at most one 9000 RPM WOT point after owner authorization. — verificar: file:results/x30-minimum-point-v1/point-result.json contiene "9000"
- [ ] X30M-RESULT-VERIFY: classify periodic/transient, separate indicated and shaft power, compare exploratorily with 15.1 kW. — verificar: file:results/x30-minimum-point-v1/report.md contiene "15.1"

Program-status is authoritative. No solver run, fabricated geometry, sweep or validation claim is authorized by this change.
