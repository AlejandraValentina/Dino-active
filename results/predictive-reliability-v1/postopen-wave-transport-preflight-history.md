# Post-opening preflight versions

`postopen-wave-transport-preflight-v3.json` is the execution preflight.
Preflight v1 preserved the source artifacts and budget result, but read the
runner-source hash map from the nested input manifest instead of the completed
run manifest. Its `source_files_sha256` was empty. V2 corrected that lookup,
but the runner changed during final implementation and its frozen runner hash
no longer matches. V3 verifies all four manifest-bound cases, each recorded
runner source hash, current runner/protocol hashes, storage reserve, and the
541.002 s projection. None of the three preflights performed solver steps.
