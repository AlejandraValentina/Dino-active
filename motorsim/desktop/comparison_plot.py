"""Overlay only primary samples from an eligible, reverified native pair."""
import csv,io,math
from .four_stroke_artifacts import require_verified_run
from .four_stroke_comparison import build_comparison


def comparison_pressure_series(references,comparison):
    snapshots=[require_verified_run(ref) for ref in references]
    current=build_comparison(*(snapshot.endpoint() for snapshot in snapshots))
    if current['comparison_id']!=comparison['comparison_id']:raise ValueError('La comparación cambió; volvé a seleccionar A/B')
    series=[]
    for side,snapshot,endpoint in zip(('A','B'),snapshots,current['endpoints']):
        raw=snapshot.snapshot.get('raw',{}).get('trace')
        if raw is None:continue
        points=[]
        for row in csv.DictReader(io.StringIO(raw.decode('utf-8'))):
            try:x=float(row['theta']);y=float(row['p'])/100000
            except (ValueError,TypeError,KeyError):continue
            if math.isfinite(x) and math.isfinite(y):points.append(dict(theta=x,value=y,classification=current['classification'],source_qualification=endpoint['source_qualification'],artifact_origin=endpoint['artifact_origin'],status=str(endpoint['artifact_origin']),run_id=endpoint['run_id'],comparison_id=current['comparison_id']))
        if points:series.append(dict(name=side+' · '+endpoint['run_id'],x_key='theta',x_label='Cigüeñal [°]',unit='bar abs',connect=True,points=points))
    return series
