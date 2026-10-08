"""Hydrodynamic contact observable; no tracer, analytical position or window."""
from math import isfinite, sqrt


def density_contact(centers, hydro, gamma):
    """Locate the unique strongest contact-dominant characteristic jump.

    hydro contains exactly (rho,u,p). Arithmetic face averages define a².
    c0=drho-dp/a² and c±=(dp/a² ± rho_bar*du/a)/2.
    A contact candidate has |c0| > |c-|+|c+|. Rank by |c0|/dx.
    Return the midpoint of the unique global maximum; reject ties/absence.
    This observable targets the single contact in T02, not arbitrary wave trains.
    """
    if len(centers) != len(hydro) or len(centers) < 2 or not isfinite(gamma) or gamma <= 1:
        raise ValueError('Invalid contact input')
    for x, w in zip(centers, hydro):
        if len(w) != 3 or not all(isfinite(v) for v in (x, *w)) or w[0] <= 0 or w[2] <= 0:
            raise ValueError('Expected finite (rho,u,p), positive rho and p')
    faces = []
    for i, (left, right) in enumerate(zip(hydro, hydro[1:])):
        dx = centers[i+1]-centers[i]
        if dx <= 0:
            raise ValueError('Unordered centers')
        rho = (left[0]+right[0])/2
        pressure = (left[2]+right[2])/2
        a2 = gamma*pressure/rho
        drho, du, dp = (r-l for l, r in zip(left, right))
        c0 = drho-dp/a2
        minus = (dp/a2-rho*du/sqrt(a2))/2
        plus = (dp/a2+rho*du/sqrt(a2))/2
        acoustic = abs(minus)+abs(plus)
        faces.append(dict(index=i, x=(centers[i]+centers[i+1])/2,
                          contact_strength=abs(c0)/dx, acoustic_strength=acoustic/dx,
                          contact_dominant=abs(c0)>acoustic))
    candidates = [f for f in faces if f['contact_dominant']]
    if not candidates:
        return dict(status='NO_CONTACT', position=None, faces=faces)
    strongest = max(f['contact_strength'] for f in candidates)
    winners = [f for f in candidates if f['contact_strength'] == strongest]
    if len(winners) != 1:
        return dict(status='AMBIGUOUS', position=None, faces=faces)
    return dict(status='UNIQUE', position=winners[0]['x'], selected_face=winners[0]['index'], faces=faces)
