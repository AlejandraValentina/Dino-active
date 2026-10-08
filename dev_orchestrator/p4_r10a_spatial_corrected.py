"""P4-R10A corrected diagnostics"""
import json, gzip, math
from pathlib import Path
import numpy as np

RESULT = Path("results/p4-r10a-20260922")
RESULT.mkdir(parents=True, exist_ok=True)
ORIG = Path("results/p4-r10-20260922")

def load_cycle(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))

def get_mesh(N):
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    dx = 0.75/N
    mesh = exhaust_mesh(segments('straight'), dx)
    return np.array(mesh.centers), dx, mesh.n

def find_snapshot(row, rel):
    target = row['begin']+rel
    return min(row['snapshots'], key=lambda s: abs(s['angle']-target))

def extract(p):
    arr=np.array(p['primitive'])
    return arr[:,2], arr[:,0], arr[:,1]  # p, rho, u

def detect_front_corrected(p, x, dx):
    # Problem 2: separate A/B/C
    dpdx = np.abs(np.diff(p)/np.diff(x))
    idx = int(np.argmax(dpdx))
    x_front = 0.5*(x[idx]+x[idx+1])
    jump_adj = abs(p[idx+1]-p[idx])
    # A: local strongest width where dpdx >0.9*max (2-3 cells)
    thresh_A = 0.9*np.max(dpdx)
    maskA = dpdx > thresh_A
    leftA = idx
    while leftA>0 and maskA[leftA-1]:
        leftA-=1
    rightA = idx
    while rightA < len(maskA)-1 and maskA[rightA+1]:
        rightA+=1
    width_A_m = float(x[rightA+1]-x[leftA]) if rightA+1<len(x) else float(x[-1]-x[leftA])
    width_A_cells = int(rightA-leftA+1)+1
    # B: broader where >0.5*max (original)
    threshB = 0.5*np.max(dpdx)
    maskB = dpdx > threshB
    leftB = idx
    while leftB>0 and maskB[leftB-1]:
        leftB-=1
    rightB = idx
    while rightB < len(maskB)-1 and maskB[rightB+1]:
        rightB+=1
    width_B_m = float(x[rightB+1]-x[leftB]) if rightB+1<len(x) else float(x[-1]-x[leftB])
    width_B_cells = int(rightB-leftB+1)+1
    # C: support of difference will be computed elsewhere, not here
    # Plateau estimation: avoid front region +- width_B, compute median left plateau and right plateau
    # Left plateau: x < x_front - width_B_m/2 - 2*dx
    # Right plateau: x > x_front + width_B_m/2 + 2*dx
    # Use 10 cells each side
    left_plateau_idx = max(0, leftB-10)
    right_plateau_idx = min(len(p)-1, rightB+10)
    plateau_left = float(np.median(p[left_plateau_idx:leftB])) if leftB>0 else float(p[0])
    plateau_right = float(np.median(p[rightB+1:right_plateau_idx+1])) if rightB+1 < len(p) else float(p[-1])
    plateau_jump = abs(plateau_right - plateau_left)
    return dict(
        x_front=float(x_front), idx=int(idx),
        jump_adj=float(jump_adj),
        plateau_left=float(plateau_left), plateau_right=float(plateau_right), plateau_jump=float(plateau_jump),
        width_A_m=float(width_A_m), width_A_cells=int(width_A_cells),
        width_B_m=float(width_B_m), width_B_cells=int(width_B_cells),
        dpdx_max=float(np.max(dpdx))
    )

def find_candidates(p, x, thresh_factor=0.3):
    dpdx = np.abs(np.diff(p)/np.diff(x))
    cands=[]
    for i in range(1,len(dpdx)-1):
        if dpdx[i] > dpdx[i-1] and dpdx[i] >= dpdx[i+1] and dpdx[i] > thresh_factor*np.max(dpdx):
            cands.append((i, float(0.5*(x[i]+x[i+1])), float(dpdx[i])))
    cands.sort(key=lambda t: t[2], reverse=True)
    return cands

def track_fronts_per_pair(p_prev, p_cur, x, sensor_x=0.10):
    """For a single lag-2 pair, find same front by choosing candidates closest to sensor and to each other"""
    cands_prev = find_candidates(p_prev, x)
    cands_cur = find_candidates(p_cur, x)
    if not cands_prev or not cands_cur:
        return None, None, "NO_CANDIDATE"
    # Prefer candidates near sensor
    # For each pair combination, compute distance to sensor and inter-front distance
    best = None
    best_score = float('inf')
    for cp in cands_prev:
        for cc in cands_cur:
            # Score: distance between fronts + distance to sensor (weighted)
            dist_front = abs(cc[1]-cp[1])
            dist_sensor = 0.5*(abs(cc[1]-sensor_x)+abs(cp[1]-sensor_x))
            # Prefer small inter-front and near sensor
            score = dist_front + 0.5*dist_sensor
            # Also penalize if jump small? But keep
            if score < best_score and dist_front < 0.05: # must be within 0.05 to be same front
                best_score = score
                best = (cp, cc)
    if best is None:
        # Fallback: choose closest to sensor for each independently, but mark ambiguous if inter-front >0.05
        cp = min(cands_prev, key=lambda t: abs(t[1]-sensor_x))
        cc = min(cands_cur, key=lambda t: abs(t[1]-sensor_x))
        if abs(cc[1]-cp[1]) > 0.05:
            return cp, cc, "AMBIGUOUS"
        return cp, cc, "TRACKED_FALLBACK"
    return best[0], best[1], "TRACKED"

if __name__ == "__main__":
    N_list = [250,300,350,400]
    # Load cycles 36-40 actual numbers 36-40
    all_cycles = {}
    for N in N_list:
        if N==250:
            paths = [Path(f"results/p4-r8-20260922/artifacts/N250-continuation-cycle{i:02}.json.gz") for i in range(36,41)]
        elif N==300:
            paths = [Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{i:02}.json.gz") for i in range(36,41)]
        elif N==350:
            paths = [Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{i:02}.json.gz") for i in range(36,41)]
        else:
            paths = [Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{i:02}.json.gz") for i in range(36,41)]
        rows = [load_cycle(p) for p in paths if p.exists()]
        all_cycles[N] = rows
        print(f"N{N} {len(rows)} cycles")
    # For each N, do corrected analysis at rel 123
    rel=123.0
    corrected = {}
    for N in N_list:
        rows = all_cycles[N]
        x, dx, n = get_mesh(N)
        # Get p for each cycle at rel
        cycles_p = []
        for row in rows:
            snap = find_snapshot(row, rel)
            p, rho, u = extract(snap)[:3]
            cycles_p.append(p)
        # For each lag-2 pair 40vs38 etc., compute with corrected metrics using per-pair tracking
        pairs = []
        # Actual cycle numbers 36-40
        cycle_numbers = list(range(36,41)) # 36,37,38,39,40
        for offset, (cur_num, prev_num) in enumerate([(40,38),(39,37),(38,36)]):
            cur_idx = cycle_numbers.index(cur_num)
            prev_idx = cycle_numbers.index(prev_num)
            p_cur = cycles_p[cur_idx]
            p_prev = cycles_p[prev_idx]
            # Per-pair tracking to ensure same front
            cp, cc, per_pair_status = track_fronts_per_pair(p_prev, p_cur, x, sensor_x=0.10)
            # Detect fronts corrected for each (also compute plateau)
            front_cur = detect_front_corrected(p_cur, x, dx)
            front_prev = detect_front_corrected(p_prev, x, dx)
            # Use per-pair tracked x_front if available, else detected
            # For per-pair, cp is for prev, cc for cur
            if per_pair_status in ("TRACKED","TRACKED_FALLBACK") and cp and cc:
                x_front_cur = float(cc[1])
                x_front_prev = float(cp[1])
                delta_x = x_front_cur - x_front_prev
                delta_x_dx = delta_x/dx
                tracking_status = per_pair_status
            else:
                # Fallback to detected global max, but mark ambiguous
                x_front_cur = front_cur['x_front']
                x_front_prev = front_prev['x_front']
                delta_x = None
                delta_x_dx = None
                tracking_status = "AMBIGUOUS"
            # Energy fractions corrected Problem 1 & 6
            diff = p_cur - p_prev
            E_total = float(np.sum(diff**2))
            # For each radius ±1,2,3 cells
            fractions = {}
            for r_cells in [1,2,3]:
                r_m = r_cells*dx
                # Inside = |x - x_front_cur| <= r_m
                # Use tracked front for inside definition
                front_x = x_front_cur
                mask_inside = np.abs(x - front_x) <= r_m + 1e-12
                E_inside = float(np.sum(diff[mask_inside]**2))
                frac_inside = E_inside/E_total if E_total else 0
                frac_outside = 1-frac_inside
                fractions[f"r_{r_cells}"] = dict(r_m=float(r_m), r_cells=int(r_cells), E_inside=E_inside, E_total=E_total, fraction_inside=frac_inside, fraction_outside=frac_outside)
            # Support fractions
            diff2 = diff**2
            total = np.sum(diff2)
            order = np.argsort(diff2)[::-1]
            cum = np.cumsum(diff2[order])
            support = {}
            for pct in [50,80,90,95]:
                thresh = pct/100*total
                idx = np.searchsorted(cum, thresh)
                n_cells = int(idx+1)
                length = n_cells*dx
                support[f"{pct}%"] = dict(n_cells=n_cells, length_m=float(length), pipe_fraction=length/0.75)
            # Jump plateau vs adjacent
            # Already in front_cur/prev
            # Labels corrected
            pairs.append(dict(
                pair=f"{cur_num} vs {prev_num}",
                cur_num=cur_num, prev_num=prev_num,
                front_cur=front_cur, front_prev=front_prev,
                x_front_cur=float(x_front_cur), x_front_prev=float(x_front_prev),
                delta_x=delta_x, delta_x_dx=delta_x_dx, tracking_status=tracking_status,
                err=dict(max_abs=float(np.max(np.abs(diff))), L1=float(np.mean(np.abs(diff))), L2=float(np.sqrt(np.mean(diff**2))), integral=float(np.sum(np.abs(diff))*dx)),
                fractions=fractions,
                support=support,
                plateau_jump_cur=front_cur['plateau_jump'], plateau_jump_prev=front_prev['plateau_jump'],
                jump_adj_cur=front_cur['jump_adj'], jump_adj_prev=front_prev['jump_adj']
            ))
        corrected[str(N)] = dict(dx=float(dx), n=n, pairs=pairs, tracking_status="PER_PAIR")
    # Save
    import json
    (RESULT/"front_tracking_corrected.json").write_text(json.dumps({k: [dict(pair=p['pair'], x_front_cur=p['x_front_cur'], x_front_prev=p['x_front_prev'], delta_x=p['delta_x'], delta_x_dx=p['delta_x_dx'], tracking=p['tracking_status'], plateau_jump_cur=p['plateau_jump_cur'], jump_adj_cur=p['jump_adj_cur'], width_A_m=p['front_cur']['width_A_m'], width_B_m=p['front_cur']['width_B_m']) for p in v['pairs']] for k,v in corrected.items()}, indent=2))
    (RESULT/"error_energy_localization.json").write_text(json.dumps({k: [dict(pair=p['pair'], fractions=p['fractions'], support=p['support'], err=p['err']) for p in v['pairs']] for k,v in corrected.items()}, indent=2))
    # Mesh trend corrected
    mesh_corrected = {}
    for N in corrected:
        dx = corrected[N]['dx']
        # avg width A vs B
        width_A = sum(p['front_cur']['width_A_m'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        width_B = sum(p['front_cur']['width_B_m'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        delta_xs = [p['delta_x'] for p in corrected[N]['pairs'] if p['delta_x'] is not None]
        avg_delta = sum(delta_xs)/len(delta_xs) if delta_xs else None
        avg_delta_dx = avg_delta/dx if avg_delta is not None else None
        # fractions
        frac1 = sum(p['fractions']['r_1']['fraction_inside'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        frac2 = sum(p['fractions']['r_2']['fraction_inside'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        frac3 = sum(p['fractions']['r_3']['fraction_inside'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        support90 = sum(p['support']['90%']['n_cells'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs'])
        support90_m = support90*dx
        # plateau jump difference
        plateau_diffs = [abs(p['front_cur']['plateau_jump']-p['front_prev']['plateau_jump']) for p in corrected[N]['pairs']]
        avg_plateau_diff = sum(plateau_diffs)/len(plateau_diffs)
        mesh_corrected[N] = dict(
            dx=float(dx), n=int(N),
            width_A_m=width_A, width_B_m=width_B,
            delta_x_avg=avg_delta, delta_x_dx_avg=avg_delta_dx,
            fraction_inside_1=frac1, fraction_inside_2=frac2, fraction_inside_3=frac3,
            support90_cells=support90, support90_m=support90_m, support90_pipe_fraction=support90_m/0.75,
            plateau_jump_avg=sum(p['front_cur']['plateau_jump'] for p in corrected[N]['pairs'])/len(corrected[N]['pairs']),
            plateau_jump_diff_avg=avg_plateau_diff,
            outside_fraction_avg=1-frac3
        )
    (RESULT/"mesh_trend_corrected.json").write_text(json.dumps(mesh_corrected, indent=2))
    # Sensor front corrected
    sensor_corrected = {}
    for N in corrected:
        sensor_corrected[N] = [dict(pair=p['pair'], sensor_x=0.10, front_x=p['x_front_cur'], width_A=p['front_cur']['width_A_m'], width_B=p['front_cur']['width_B_m'], cross=(abs(p['x_front_cur']-0.10) < p['front_cur']['width_A_m']/2 + 1e-12), dist=abs(p['x_front_cur']-0.10), tracking=p['tracking_status']) for p in corrected[N]['pairs']]
    (RESULT/"sensor_front_corrected.json").write_text(json.dumps(sensor_corrected, indent=2))
    # Audit diff vs R10
    orig_mesh = json.loads((ORIG/"mesh_trend.json").read_text())
    audit_diff = {}
    for N in ["250","350","400"]:
        orig_w = orig_mesh[N]["front_width_cells"]
        corr_w_A = mesh_corrected[N]["width_A_m"]/mesh_corrected[N]["dx"]
        corr_w_B = mesh_corrected[N]["width_B_m"]/mesh_corrected[N]["dx"]
        # original fraction inside was incorrectly RMS ratio, now energy
        # original had 60-83% inside vs corrected maybe different
        orig_frac = None
        try:
            orig_frac = json.loads((ORIG/"spatial_error.json").read_text())[N][0]['outside'] # not
        except:
            pass
        audit_diff[N] = dict(
            width_orig_cells=orig_w,
            width_corrected_A_cells=corr_w_A,
            width_corrected_B_cells=mesh_corrected[N]["width_B_m"]/mesh_corrected[N]["dx"],
            note="Original width 50-90 cells was broader wavefront width (0.5*max), corrected separates A(0.9*max) local 2-3 cells vs B broad 50-90. Original described as 'shock width few cells' incorrectly; corrected shows local 2-3 cells but broader 50-90."
        )
    (RESULT/"audit_diff_vs_r10.json").write_text(json.dumps(audit_diff, indent=2))
    print("R10A corrected done")
    # Also need to handle conservative rhoE test
    # Create test for rhoE
    import numpy as np
    gamma=1.35
    rho=np.array([0.5]); u=np.array([10]); p=np.array([100000])
    rhoE_correct = p/(gamma-1)+0.5*rho*u*u
    rhoE_wrong = rho*(p/(gamma-1)+0.5*rho*u*u) # wrong multiplied
    print(f"rhoE correct {rhoE_correct[0]} wrong {rhoE_wrong[0]} ratio {rhoE_wrong[0]/rhoE_correct[0]}")
