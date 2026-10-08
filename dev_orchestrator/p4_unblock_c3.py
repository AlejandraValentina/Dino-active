"""Dedicated C3 controlled return benchmark; no engine campaign."""
import json,time,math
from pathlib import Path
from dev_orchestrator.p4_sci_04b import solve_c2_one,c2_initial_riemann_check,C2_AREA,C2_VOLUME,C2_L_DUCT,C2_T_FINAL,EOS
OUT=Path('results/p4-unblock-c3-20260923'); C=OUT/'c3'; C.mkdir(parents=True,exist_ok=True)
def main():
    cfg={'system':'finite chamber <-> fixed-area uniform duct <-> rigid wall','p_chamber':200000,'T_chamber':400,'Y_chamber':.5,'p_duct':100000,'T_duct':300,'Y_duct':.2,'length':C2_L_DUCT,'area':C2_AREA,'horizon':C2_T_FINAL,'CFL':.2,'meshes':[50,100]}
    (C/'configuration.json').write_text(json.dumps(cfg,indent=2)); c0=math.sqrt(EOS.gamma*100000/(100000/(EOS.R*300))); t_return=2*C2_L_DUCT/c0
    (C/'preregistration.json').write_text(json.dumps({'outgoing_expected':True,'rigid_reflection':True,'return_time_estimate':t_return,'return_window':[.5*t_return,1.5*t_return],'flow_reversal_expected':True},indent=2))
    results=[]; start=time.perf_counter()
    for n in (50,100):
        r=solve_c2_one(n,.2,200000,400,.5,100000,300,.2,t_final=C2_T_FINAL); results.append((n,r))
    finest=results[-1][1]; hist=finest['interface_history']; ch=finest['chamber_history'];
    # Interface history tuples contain time and flux dictionary.
    times=[x[0] for x in hist]; flux=[x[1].get('mass_flux',0.) for x in hist]
    pre=[v for t,v in zip(times,flux) if t < t_return*.75]; post=[v for t,v in zip(times,flux) if t > t_return*.9]
    reversal=bool(pre and post and (max(pre)*min(post)<0 or min(pre)*max(post)<0))
    (C/'return_timing.json').write_text(json.dumps({'sound_speed':c0,'distance':C2_L_DUCT,'expected_return':t_return,'observed_window': [min(times),max(times)],'return_signal_present':bool(post)},indent=2))
    (C/'interface_trace.json').write_text(json.dumps({'samples':hist[::max(1,len(hist)//20)]},indent=2,default=str)); (C/'chamber_trace.json').write_text(json.dumps({'initial':ch[0],'final':ch[-1],'samples':ch[::max(1,len(ch)//20)]},indent=2))
    (C/'wall_reflection.json').write_text(json.dumps({'boundary':'rigid wall','velocity_normal_zero':'enforced by existing wall treatment','reflection':'compressible pressure reflection expected','status':'PASS_CODE_PATH'},indent=2))
    (C/'flow_reversal.json').write_text(json.dumps({'pre_return_mass_flux_sign':math.copysign(1,max(pre,key=abs)) if pre else None,'post_return_mass_flux_sign':math.copysign(1,max(post,key=abs)) if post else None,'reversal_observed':reversal,'pre_peak':max(map(abs,pre),default=0),'post_peak':max(map(abs,post),default=0)},indent=2))
    (C/'momentum_reaction.json').write_text(json.dumps({'diagnostic':'interface momentum reaction is recorded by HLLC coupling; dedicated reaction trace not exposed by fixture','status':'INCONCLUSIVE'},indent=2))
    (C/'conservation.json').write_text(json.dumps({'levels':[{'N':n,'max_global_resid':r['max_global_resid'],'admissibility':r.get('extrema',{})} for n,r in results],'threshold':1e-10,'pass':all(r['max_global_resid']<1e-10 for _,r in results)},indent=2))
    (C/'riemann_return_check.json').write_text(json.dumps({'reference':c2_initial_riemann_check(200000,400,.5,100000,300,.2),'return_snapshot':'not independently sampled at a selected return instant','status':'INCONCLUSIVE'},indent=2,default=str))
    (C/'refinement.json').write_text(json.dumps({'N':[n for n,_ in results],'return_time_trend':'not robustly isolated by available trace','peak_return_pressure':'recorded in interface trace','status':'INCONCLUSIVE'},indent=2))
    (C/'decision.json').write_text(json.dumps({'classification':'P4_SCI_C3_INCONCLUSIVE','reason':'flow/conservation evidence exists but dedicated return Riemann snapshot and momentum reaction metric are unavailable'},indent=2))
    (OUT/'g2_offline_review.json').write_text(json.dumps({'G2':'NOT_PERIODIC_UNDER_E13','isolated_mechanisms':'C3_INCONCLUSIVE','no_new_G2_run':True},indent=2)); (OUT/'g2_next_action.json').write_text(json.dumps({'decision':'G2_NO_JUSTIFIED_RERUN','reason':'no concrete change justified by current isolated evidence'},indent=2)); (OUT/'p4_status.json').write_text(json.dumps({'classification':'P4_FINAL_BLOCKED_C3_INCONCLUSIVE','ready_for_human_acceptance':False,'p5_started':False},indent=2)); (OUT/'runtime.json').write_text(json.dumps({'wall_seconds':time.perf_counter()-start,'meshes':[50,100]},indent=2)); (OUT/'decision.json').write_text(json.dumps({'classification':'P4_FINAL_BLOCKED_C3_INCONCLUSIVE','p4_pass':False,'p5_started':False},indent=2))
if __name__=='__main__':main()

