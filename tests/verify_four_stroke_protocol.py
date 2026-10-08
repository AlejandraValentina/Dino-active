"""Cuatro ejecuciones restantes del protocolo R2, solo con --execute.

Sin esa opción relee y contrasta evidencia; nunca repite cálculos existentes.
Presupuesto compartido con A/B/C históricos, C50 y el recorrido GUI.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from motorsim.reference_results import load_result
from motorsim.sweep import load_sweep
from motorsim.simulation import sensitivity

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--execute',action='store_true')
args=parser.parse_args();root=args.root
ledger_path=root/'protocol.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
assert ledger['gate_passed']
sweep=load_sweep(root/'gui-sweep/series.json');assert sweep['index']['state']=='converged'
modified=load_result(root/'gui-compression/manifest.json');assert modified['status']=='converged'
def raw(result):return dict(result['result'],last_two_cycles=result['samples']['cycles'])
original=json.loads((root.parent/'B-100/result.json').read_text(encoding='utf-8'))
gui=raw(sweep['results'][1])
assert gui['cycles']==original['cycles'] and gui['last_two_cycles']==original['last_two_cycles']
assert gui['rhs_evaluations']==original['rhs_evaluations']
ledger['gui_console_reference_exact']=True
cases=[('C100-2500',sweep['results'][0]),('C100-3500',sweep['results'][2]),
       ('C100-compression-8.2',modified),('2T-B100-regression',None)]
for name,baseline in cases:
    folder=root/name
    if args.execute:
        assert not folder.exists(),f'No repetir {folder}'
        assert ledger['integration_seconds']+60<=720
        command=[sys.executable,'-u','-m','motorsim.reference_run','--output',str(folder)]
        if baseline:
            request=root/(name+'-inputs.json')
            request.write_text(json.dumps(baseline['inputs'],ensure_ascii=False,indent=2),encoding='utf-8')
            command+=['--project-input',str(request),'--profile-c-check']
        else:command+=['--cycle','2T']
        print('START',name,flush=True)
        with (root/(name+'-process.log')).open('x',encoding='utf-8') as stream:
            process=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=75)
        result=load_result(folder/'manifest.json')
        ledger['runs'].append(dict(name=name,seconds=result['result']['seconds'],
            converged=result['status']=='converged',stop=result['result']['stop']))
        ledger['integration_seconds']+=result['result']['seconds']
        ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
        assert process.returncode==0 and result['status']=='converged',result['result']['stop']
    else:result=load_result(folder/'manifest.json')
    if baseline:
        b,c=raw(baseline),raw(result)
        comparison=sensitivity([b,b,c],cylinder=1)
        ledger.setdefault('BC_checks',{})[name]=dict(tolerances_passed=comparison['tolerances_passed'],
            differences=comparison['fine'],trend='Not applicable: two profiles only')
        assert comparison['tolerances_passed'],comparison
    else:
        before=load_result(Path('results/simulacion-2t/integracion-ui-20260915/manifest.json'))
        for key in ('cycles','rhs_evaluations'):assert result['result'][key]==before['result'][key],key
        assert result['samples']==dict(before['samples'],run_id=result['samples']['run_id'])
        ledger['two_stroke_regression_exact']=True
    ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS',name,'seconds',result['result']['seconds'],'total',ledger['integration_seconds'],flush=True)
print('COMPLETE; total integration seconds',ledger['integration_seconds'],flush=True)
