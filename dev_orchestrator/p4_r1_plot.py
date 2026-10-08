"""Plot saved P4-R1 evidence; matplotlib is an offline reporting tool only."""
import argparse
import gzip
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def plot(folder):
    cases=[json.loads(gzip.decompress(p.read_bytes())) for p in (folder/'run/artifacts/cases').glob('*.gz')]
    fig,axes=plt.subplots(2,1,figsize=(11,8),layout='constrained')
    for row in sorted(cases,key=lambda r:r['N']):
        if row['CFL']!=.4:continue
        ax=axes[0 if row['kind']=='blowdown' else 1]
        s=row['signal'];label=f"N={row['N']}"+(' (parcial)' if not row['complete'] else '')
        ax.plot([t*1000 for t in s['times']],[v/1000 for v in s['pressure']],
                label=label,linestyle='-' if row['complete'] else '--',linewidth=1.3)
    axes[0].set_title('Descarga: sensor físico x = 0,1 m · CFL 0,4')
    axes[0].axvline(10/18,color='gray',linestyle=':',linewidth=1,label='Apertura / cierre')
    axes[0].axvline(190/18,color='gray',linestyle=':',linewidth=1)
    partial=next(r for r in cases if r['N']==800)
    if not partial['complete']:
        axes[0].axvline(partial['metrics']['interval'][1]*1000,color='tab:red',linestyle=':',label='Corte N800: 900 s')
    axes[1].set_title('Control débil: puerto constante · sensor x = 0,1 m · CFL 0,4')
    for ax in axes:
        ax.set_xlabel('Tiempo físico [ms]');ax.set_ylabel('Presión [kPa]')
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('P4-R1 · solver congelado · sin aceptación de P4',fontsize=13)
    for extension in ('png','svg'):
        p=folder/f'signals.{extension}';fig.savefig(p,dpi=160)
        if extension=='svg':p.write_text('\n'.join(line.rstrip() for line in p.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('folder',type=Path)
    plot(parser.parse_args().folder)
