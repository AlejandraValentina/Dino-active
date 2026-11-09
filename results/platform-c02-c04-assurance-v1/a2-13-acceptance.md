# A2-13 acceptance source check

Command (source, offscreen):

```text
python -c "from motorsim.desktop.acceptance_smoke_4t import main; raise SystemExit(main(['--output', <temp>, '--historical-summary', <V1 summary>, '--run']))"
```

Result: `PASS`, 4 captures, historical V1 result imported as
`LEGACY_UNVERIFIED`, one bounded 4T run `completed`/`NOT_CONVERGED`, and the
CSV/report exports included both records. No packaged EXE/build was used.
