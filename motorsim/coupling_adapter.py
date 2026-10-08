"""State-only bridge to existing MotorSim 0D layouts. No engine connections."""
from math import isclose
from .coupling import ChamberState
from .gas1d.eos import IdealGas, InvalidState


def chamber_from_model(model, angle, state, node):
    """Read one named control volume without changing the model or its state."""
    if len(state)!=model.layout.size:raise ValueError('0D state/layout mismatch')
    index=model.layout.cv.index(node)
    volume=model.geometry(angle)[0][index]
    chamber=ChamberState(*state[3*index:3*index+3],volume)
    eos=IdealGas(R=model.case.gas_r,gamma=model.case.gamma)
    chamber.thermodynamics(eos)
    return chamber,eos


def state_with_chamber(model, angle, state, node, chamber):
    """Copy m/U/F back; retain other volumes and every legacy ledger entry."""
    previous,eos=chamber_from_model(model,angle,state,node)
    chamber.thermodynamics(eos)
    if not isclose(chamber.volume,previous.volume,rel_tol=1e-12,abs_tol=0.):
        raise InvalidState('Chamber volume does not match model geometry at angle')
    index=model.layout.cv.index(node);result=list(state)
    result[3*index:3*index+3]=[chamber.mass,chamber.internal_energy,chamber.fresh_mass]
    return result
