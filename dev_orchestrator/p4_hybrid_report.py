"""Offline audit/plots of the saved hybrid preflight; never integrates."""
import argparse,gzip,json
from math import fsum
from pathlib import Path
from motorsim.hybrid_exhaust import LegacySources,HybridSystem
from motorsim.gas1d.eos import IdealGas
from .p2_campaign import write


def report(folder):
    row=json.loads(gzip.decompress((folder/'p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    model=LegacySources();eos=IdealGas();segments=row['segments'];traces=[];states=[]
    for s in segments:
        r=s['result'];system=HybridSystem(model,s['start_angle'],r['history'][0]['chamber'],350 if s['start_angle']==350 else None)
        # For the heat segment F is the constant transformed coordinate, also in first accepted state.
        for step in r['stages']:
            for t in step['traces']:
                traces.append(t);full=system.physical(t['chamber'],t['time'])
                nodes=model.evaluate(t['angle'],full,system.heat)[1][0]
                volumes=model.geometry(t['angle'])[0]
                states.extend(dict(rho=full[3*i]/volumes[i],p=nodes[i][0],T=nodes[i][1],Y=nodes[i][2]) for i in range(3))
    physical0=row['initial_inventory'];physical1=[fsum(row['state'][k::3])+fsum(c[j] for c in row['cells']) for k,j in enumerate((0,2,3))]
    ledger=[fsum(s['result']['external'][k]-(s['analytical_burn'] if k==2 else 0.) for s in segments) for k in range(3)]
    scale=[physical0[0],physical0[1],physical0[0]]
    residual=[(b-a-e)/z for a,b,e,z in zip(physical0,physical1,ledger,scale)]
    back=[t for t in traces if t['exchange'][0]>0];closed=[t for t in traces if t['area']==0]
    data=dict(state='P4_BLOCKED_PERFORMANCE',complete_cycles=1,multicycle_executed=False,G2_executed=False,
        phase_interval=[row['begin'],row['end']],runtime=row['cycle_wall_seconds'],projection_30=row['cycle_wall_seconds']*30,
        budget=600,mesh_N=250,G2_defined_N=251,global_initial=physical0,global_final=physical1,external=ledger,
        independently_resummed_residual=residual,internal_port_exchange=row['port_integral'],
        max_stage_residual=max(s['result']['max_stage_residual'] for s in segments),
        max_segment_global_residual=max(s['result']['max_global_residual'] for s in segments),
        pipe_extrema={k:(max if k=='Y_max' else min)(s['result']['extrema'][k] for s in segments) for k in ('rho','p','T','Y_min','Y_max')},
        saved_0D_trace_extrema={k:[min(v[k] for v in states),max(v[k] for v in states)] for k in ('rho','p','T','Y')},
        zeroD_extent_note='Extrema of saved RHS traces only; frozen solver validates also intermediate Euler and accepted states.',
        closed_traces=len(closed),closed_exchange_exact_zero=all(all(v==0 for v in t['exchange']) for t in closed),
        backflow_traces=len(back),backflow_species_max_error=max((abs(t['exchange'][2]-t['exchange'][0]*t['pipe_face'][3]) for t in back),default=None),
        counts={k:sum(s['result']['counts'][k] for s in segments) for k in ('rhs','HLLC','HLLE','rejected','characteristic')},
        accepted_steps=sum(len(s['result']['history']) for s in segments),
        sensor_positions=segments[0]['result']['sensor_positions'],
        work_indicated_J=row['work_indicated_J'],power_indicated_W=row['power_indicated_W'],torque_indicated_Nm=row['torque_indicated_Nm'],
        diagnostic_only_not_periodic=True,analytical_burn_kg=row['analytical_burn'],heat_numeric_J=row['heat_numeric'],
        heat_primitive_J=model.case.fresh_energy_j_kg*row['analytical_burn'],
        E12='PASS for measured cycle only',E15='PASS for measured cycle only',E13='NOT_EXECUTED',E14='NOT_EXECUTED',
        reflected_wave_timing=None,P4_PASS=False)
    write(folder/'hybrid-audit.json',data)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    hs=row['history'];x=[h['angle'] for h in hs]
    fig,ax=plt.subplots(3,2,figsize=(12,10),layout='constrained')
    for a,key,scale,label in ((ax[0,0],'p_cyl',.001,'Presión C [kPa]'),(ax[0,1],'p_port',.001,'Presión cara puerto, etapa 2 [kPa]'),
            (ax[1,0],'mass_flux_port',1000,'Flujo medio hacia C [g/s]'),(ax[1,1],'W_indicated',1,'Trabajo indicado acumulado [J]'),
            (ax[2,0],'A_exhaust',1e6,'Área geométrica [mm²]')):
        a.plot(x,[h[key]*scale for h in hs],lw=1);a.set_ylabel(label)
    for i,pos in enumerate(data['sensor_positions']):ax[2,1].plot(x,[h['sensors_p_u_M_Y'][i][0]/1000 for h in hs],label=f'x={pos:g} m',lw=1)
    ax[2,1].set_ylabel('Presión sensores [kPa]');ax[2,1].legend(fontsize=8)
    for a in ax.flat:a.set_xlabel('Ángulo [°]');a.grid(alpha=.2)
    fig.suptitle('P4C · G1 sintético · primer ciclo transitorio · NO periódico\nSTOP por coste; sin G2 ni demostración de onda de retorno')
    for ext in ('png','svg'):
        path=folder/f'hybrid-traces.{ext}';fig.savefig(path,dpi=140)
        if ext=='svg':path.write_text('\n'.join(s.rstrip() for s in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);report(p.parse_args().folder)
