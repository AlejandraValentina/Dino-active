"""Plot saved numerical evidence only; no simulations or curve fitting."""
import argparse
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load


def plot(root,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if output.exists():raise FileExistsError('preserve plot')
    base=root/'preopen-wave-transport-run-v1';a=load(base/'analysis-complete-v3.json')
    fig,axes=plt.subplots(2,2,figsize=(11,7.5));colors=['#2563eb','#ea580c','#15803d','#7e22ce']
    for name,color in zip(('p0-88','p0-176','p0-352','p1-176'),colors):
        cfg=load(base/'run'/name/'configuration.json');f=load(base/'run'/name/'frames.json')[-1];state=f['state'];path=next(p for p in cfg['ducts'] if p['id']=='exhaust')
        x=path['mesh']['centers'];q=np.array(state['ducts']['exhaust']);s=np.array(state['species']['ducts']['exhaust']);pressure=(cfg['eos']['gamma']-1)*(q[:,2]-.5*q[:,1]**2/q[:,0])
        style='--' if name.startswith('p1') else '-'
        axes[0,0].plot(x,pressure/1e5,style,color=color,label=name,linewidth=1.1)
        axes[0,1].plot(x,s[:,3]/s.sum(axis=1),style,color=color,linewidth=1.1)
        phases=a['cases'][name]['phase_material_marker_change']
        axes[1,0].plot([p['phase_deg'] for p in phases],[p['common_original88_material_bin_change']['norms']['burned']['L1'] for p in phases],style+'o',color=color,markersize=3,linewidth=1.1)
    names=['p0-88','p0-176','p0-352'];values=[a['cases'][n]['outlet']['gross_out_kg']*1e6 for n in names]
    axes[1,1].bar([88,176,352],values,width=[32,55,95],color=colors[:3]);axes[1,1].set_ylim(0,35)
    for x,value in zip((88,176,352),values):axes[1,1].text(x,value+.4,f'{value:.3f}',ha='center',fontsize=8)
    for ax,title in zip(axes.flat,['Presión al final del arco, fase60°','Quemados al final del arco, fase60°','Cambio material: mismos intervalos originales88','Masa saliente bruta durante0–60°']):
        ax.set_title(title,fontsize=10);ax.grid(True,alpha=.22)
    axes[0,0].legend(fontsize=8);axes[0,0].set_ylabel('Presión [bar]');axes[0,1].set_ylabel('Fracción másica de quemados [1]')
    for ax in axes[0]:ax.set_xlabel('Posición en escape [m]')
    axes[1,0].set_xlabel('Fase de cigüeñal [grados]');axes[1,0].set_ylabel('L1 de ΔY, peso de masa [1]')
    axes[1,1].set_xlabel('Celdas totales');axes[1,1].set_ylabel('Masa [mg]');axes[1,1].set_xticks([88,176,352])
    fig.suptitle('Dino2T — diagnóstico transitorio antes de abrir escape',fontsize=13)
    fig.text(.5,.012,'Mismo estado físico P0. P1 contrasta subcelda. Sin periodicidad ni validación experimental; no es una curva de potencia.',ha='center',fontsize=8)
    fig.tight_layout(rect=[0,.035,1,.96]);fig.savefig(output,dpi=160);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();plot(a.root,a.output)
