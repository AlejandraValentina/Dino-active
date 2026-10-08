# Roadmap executor checkpoint

P8 is closed conditionally at commit `437a66fa4cbdf58c3393e7aaf81ca426c5419ebe`.
The durable campaign is `results/p8-wide-rpm-20260927/p8-wide-rpm.json` with anchors
2500/5000/8000/11000/15000 rpm. All recorded measured gates pass, including
restart with the authoritative CFL+event-cut scheduler, deterministic replay,
non-vacuous P7 burn, global mass/energy conservation and admissibility.

`dev_orchestrator/roadmap_executor.py` now reconstructs state from that durable
campaign instead of writing the obsolete P5-B blocked state. It cross-checks
the consolidated JSON against every `anchor-*.json` file and the CSV before it
records a conditional P8 closure.

P4 remains `BLOCKED / NOT_GRANTED`. Independent review remains pending.
P9 remains `STOPPED` and is not authorized by this checkpoint. No automatic
phase transition is permitted from this state.
