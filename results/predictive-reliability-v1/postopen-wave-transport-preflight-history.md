# Post-opening preflight versions

`postopen-wave-transport-preflight-v4.json` is the execution preflight for
activation v2 and the fresh output path.
Preflight v1 preserved the source artifacts and budget result, but read the
runner-source hash map from the nested input manifest instead of the completed
run manifest. Its `source_files_sha256` was empty. V2 corrected that lookup,
but the runner changed during final implementation and its frozen runner hash
no longer matches. V3 bound that runner version, but was superseded after the
first invocation exposed the FAST-terminal serialization contract. V4 binds
the corrected runner and v2 activation, accounts for the preserved 27.797 s
first attempt (572.203 s remaining of the 600 s cap), verifies all four
manifest-bound cases and recorded runner source hashes, and passes storage
reserve with the 541.002 s projection. All four preflights performed zero
solver steps.
