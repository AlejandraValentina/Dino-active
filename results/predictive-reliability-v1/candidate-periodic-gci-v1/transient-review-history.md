# Transient review artifact sequence

`transient-review-v4.json` is the accepted read-only review. Earlier outputs
are preserved as run provenance and superseded:

- v1 reported raw absolute conservation residuals against a normalized gate;
  its conservation boolean is invalid.
- v2 corrected the normalized residual calculation and is missing the budget
  feasibility check.
- v3 includes budget feasibility, but its continuation wording did not combine
  the trend and budget results.
- v4 includes both corrections and is the only report to use for decisions.

No solver data, thresholds, parameters, or source artifacts were modified.
