"""P4 IDEAL_PORT_BASELINE; isolated, no changes to the accepted P3 kernel."""
from dataclasses import dataclass
from math import isfinite
from .coupling import interface_flux
from .gas1d.boundary import Boundary
from .gas1d.eos import IdealGas
from .kinematics import piston_position
from .ports import uncovered_area, crossing_angle


@dataclass(frozen=True)
class ExhaustPort:
    stroke: float
    rod: float
    top: float
    height: float
    width: float

    @classmethod
    def from_project(cls, project):
        port=next(p for p in project.ports if p.function=='escape')
        return cls(project.stroke_mm,project.rod_length_mm,port.top_mm,port.height_mm,port.width_mm)

    def area(self,angle):
        return uncovered_area(self.width,self.height,piston_position(self.stroke,self.rod,angle)-self.top)*1e-6

    def events(self,pipe_area):
        depths=(self.top,self.top+self.height,self.top+pipe_area*1e6/self.width)
        angles={0.,180.,360.}
        for depth in depths:
            if 0<depth<self.stroke:
                opening=crossing_angle(self.stroke,self.rod,depth)
                angles.update((opening,360-opening))
        return sorted(angles)


def port_flux(chamber,pipe,geometric_area,pipe_area,*,eos=None):
    eos=eos or IdealGas()
    if not all(isfinite(x) for x in (geometric_area,pipe_area)) or geometric_area<0 or pipe_area<=0:
        raise ValueError('Invalid port area')
    effective=min(geometric_area,pipe_area)
    wall,speeds,wall_reason=Boundary('wall').flux(pipe,-1,eos)
    closed_force=(pipe_area-effective)*wall[1]
    if effective==0:
        return dict(flux=tuple(pipe_area*x for x in wall),exchange=(0.,0.,0.),
                    speeds=speeds,open_reaction=0.,closed_reaction=-closed_force,
                    area=0.,HLLC=int(wall_reason is None),HLLE=int(wall_reason is not None))
    coupling=interface_flux(chamber,pipe,effective,-1,eos=eos)
    flux=list(coupling.flux_x);flux[1]+=closed_force
    bounds=(min(speeds[0],coupling.wave_speeds[0]),coupling.wave_speeds[1],max(speeds[2],coupling.wave_speeds[2]))
    return dict(flux=tuple(flux),exchange=tuple(coupling.outward[k] for k in (0,2,3)),
                speeds=bounds,open_reaction=coupling.outward[1],closed_reaction=-closed_force,
                area=effective,HLLC=int(wall_reason is None)+int(coupling.fallback_reason is None),
                HLLE=int(wall_reason is not None)+int(coupling.fallback_reason is not None))
