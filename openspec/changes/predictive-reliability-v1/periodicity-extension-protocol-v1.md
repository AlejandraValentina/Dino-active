# Single extension after trend diagnosis, 2026-10-27
Evidence: prior max threshold ratio399->113, lag2 worse than lag1; last210failed
metrics mixed67improving/137worsening/6stable. One extension resolves whether
remaining residual front relaxes; no expectation/requirement of PASS.
Restore nativecycle11 and replay persisted detector history only, not physical
historical cycles. Preserve partialcycle12 from earlier invocation separately;
its40degrees are not a full native checkpoint. Frozen source/config/criteria.
At most6cycles12..17,120s solver/180s wall,16MiB,preflight; checkpoint everycycle.
After at least3new complete cycles stop if median worst ratio over last3 has
not improved5% versus previous3 and medianp90 has not decreased. This is a
resource stopping rule, never a relaxation of acceptance/detector thresholds.
Stop on candidate period, error or budget; do not automatically extend again.
Record solve/restore/serialization/detector time separately. No primary audit in
this invocation; use previous measured audit76.87s/cycle as labelled reference.
