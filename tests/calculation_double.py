"""Doble de proceso cooperativo: protocolo real, cero pasos de integración."""
from dataclasses import asdict
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from motorsim import reference_run
from motorsim.simulation import StopCalculation, sample


def diagnostic_run(profile, monitor, model, trace=None):
    started=time.monotonic(); state=model.initial_state(); angle=model.case.initial_angle_deg
    row=sample(angle,state,model.evaluate(angle,state)[1],rpm=model.case.rpm,
               initial_angle=angle,layout=model.layout)
    try:
        while True:
            monitor(1,angle,0)
            time.sleep(.01)
    except StopCalculation as exc:
        return dict(profile=asdict(profile),converged=False,cycles=[],last_two_cycles=[],
                    partial=dict(angle_deg=angle,state=state[:model.layout.physical],samples=[row]),
                    seconds=time.monotonic()-started,stop=str(exc))


if __name__=='__main__':
    reference_run.run_adaptive=diagnostic_run
    raise SystemExit(reference_run.main())
