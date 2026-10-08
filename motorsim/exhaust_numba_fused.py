"""R5 fused backend: same kernels as exhaust_numba but with FUSED_ENABLED=True.
No scientific change, only structural fusion for performance.
"""
from .exhaust_numba import (
    validate, flux, conservative, estimate_wave_speeds, hlle_flux, hllc_flux, faces, hllc,
    primitive_numeric, primitive, admissible, reconstruct_numeric,
    primitive_inplace, reconstruct_inplace, fused_interior,
    Kernel,
)
from .exhaust_numba import *  # noqa
# Enable fused path for exhaust_numpy solver
FUSED_ENABLED = True

def solve_exhaust(*args, **kwargs):
    from .exhaust_numpy import solve_exhaust as reference
    import sys
    return reference(*args, numeric_backend=sys.modules[__name__], **kwargs)
