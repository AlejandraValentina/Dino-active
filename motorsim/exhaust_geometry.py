"""Internal adapter from existing duct segments to the accepted quasi-1D mesh."""
from .gas1d.mesh import segments_mesh


def exhaust_mesh(segments,dx_target):
    rows=[]
    for segment in segments:
        segment.validate()
        rows.append(dict(length=segment.length_mm,start_diameter=segment.start_diameter_mm,end_diameter=segment.end_diameter_mm))
    return segments_mesh(rows,dx_target)
