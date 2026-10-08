"""G2-v2 entry point; the original compact-only run is preserved in Git history.

This module delegates to the durable acquisition. It never overwrites the
historical evidence in ``results/p4-g2-v2-20260929``.
"""
from dev_orchestrator.p4_g2_v2_recovery import ROOT, run


def main():
    return run(ROOT)


if __name__ == "__main__":
    import json

    print(json.dumps(main(), allow_nan=False), flush=True)
