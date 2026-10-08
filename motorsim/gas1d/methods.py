"""Explicit experimental mode selection; frozen FIRST_ORDER remains untouched."""
from .solver import solve as first_order
from .second_order import solve as second_order


def solve(*args, method='FIRST_ORDER', **kwargs):
    if method == 'FIRST_ORDER':return first_order(*args, **kwargs)
    if method == 'MUSCL_SSPRK2':return second_order(*args, **kwargs)
    raise ValueError('Unknown gas1d method: '+str(method))
