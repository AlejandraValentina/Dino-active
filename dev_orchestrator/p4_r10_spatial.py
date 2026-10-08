"""P4-R10 spatial shock localization using existing G1-cycle snapshots"""
import json, gzip, math
from pathlib import Path
import numpy as np
from bisect import bisect_right

RESULT = Path("results/p4-r10-20260922")
RESULT.mkdir(parents=True, exist_ok=True)

def load_cycle(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))

def get_mesh_centers(N):
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    dx = 0.75/N
    mesh = exhaust_mesh(segments('straight'), dx)
    return np.array(mesh.centers), np.array(mesh.volumes), dx, mesh.n

def find_snapshot_for_phase(row, rel_phase):
    """rel_phase 0-360 relative to begin, find snapshot closest"""
    begin = row['begin']
    target = begin + rel_phase
    snaps = row['snapshots']
    # snaps have angle
    best = min(snaps, key=lambda s: abs(s['angle'] - target))
    return best

def extract_p_rho_u_T_Y(snapshot):
    # primitive is list of [rho,u,p,Y] per cell
    prim = snapshot['primitive']
    arr = np.array(prim) # n,4
    rho = arr[:,0]; u = arr[:,1]; p = arr[:,2]; Y = arr[:,3]
    # T = p/(rho*R)
    R=287; T = p/(rho*R)
    return p, rho, u, T, Y, arr

def detect_front(p, x, dx):
    """Detect front via max |dp/dx| and also relative gradient"""
    dpdx = np.abs(np.diff(p) / np.diff(x))
    idx = int(np.argmax(dpdx))
    x_front = 0.5*(x[idx]+x[idx+1])
    p_left = p[idx]; p_right = p[idx+1]
    jump = abs(p_right - p_left)
    # front width: distance where |dp/dx| > 0.5*max ?
    thresh = 0.5*np.max(dpdx)
    # find contiguous region around idx where dpdx > thresh
    mask = dpdx > thresh
    # expand from idx outward
    left = idx
    while left>0 and mask[left-1]:
        left-=1
    right = idx
    while right < len(mask)-1 and mask[right+1]:
        right+=1
    width_m = float(x[right+1]-x[left]) if right+1 < len(x) else float(x[-1]-x[left])
    width_cells = int(right - left + 1) + 1
    # also relative gradient max
    rel_grad = dpdx[idx]/max(p_left, p_right) if max(p_left,p_right) else 0
    return dict(
        x_front=float(x_front),
        idx=int(idx),
        p_left=float(p_left), p_right=float(p_right),
        jump=float(jump),
        dpdx_max=float(np.max(dpdx)),
        rel_grad=float(rel_grad),
        width_m=float(width_m),
        width_cells=int(width_cells),
        dpdx=dpdx
    )

def spatial_error(p_a, p_b, x, dx):
    diff = p_a - p_b
    max_abs = float(np.max(np.abs(diff)))
    L1 = float(np.mean(np.abs(diff)))
    L2 = float(np.sqrt(np.mean(diff*diff)))
    integral = float(np.sum(np.abs(diff))*dx) # approx dx uniform
    # normalized
    denom = float(np.max(np.abs(p_a)))
    max_norm = max_abs/denom if denom else 0
    L2_norm = L2/denom if denom else 0
    return dict(max_abs=max_abs, L1=L1, L2=L2, integral=integral, max_norm=max_norm, L2_norm=L2_norm)

def error_outside_front(p_a, p_b, x, front, radii_m):
    """radii_m list like [1*dx,2*dx,3*dx]"""
    results = {}
    for r in radii_m:
        mask = np.abs(x - front['x_front']) > r
        if np.sum(mask)==0:
            results[f"r_{r:.4f}"] = None
            continue
        diff = p_a[mask] - p_b[mask]
        max_abs = float(np.max(np.abs(diff)))
        L2 = float(np.sqrt(np.mean(diff*diff)))
        L1 = float(np.mean(np.abs(diff)))
        integral = float(np.sum(np.abs(diff))* (x[1]-x[0]))
        # percentage of total error
        total_l2 = float(np.sqrt(np.mean((p_a-p_b)**2)))
        pct = (L2/total_l2*100) if total_l2 else 0
        # Actually we want percentage outside vs total
        # Compute total outside vs total
        results[f"r_{r:.4f}"] = dict(max_abs=max_abs, L2=L2, L1=L1, integral=integral, pct_L2_outside=pct, pct_L2_inside=100-pct)
    return results

def support_fraction(p_a, p_b, x):
    diff2 = (p_a - p_b)**2
    total = np.sum(diff2)
    if total==0:
        return {}
    # sort by diff2 descending, compute cumulative
    order = np.argsort(diff2)[::-1]
    cum = np.cumsum(diff2[order])
    out={}
    for pct in [50,80,90,95]:
        thresh = pct/100 * total
        idx = np.searchsorted(cum, thresh)
        n_cells = int(idx+1)
        # physical length: n_cells * dx
        length = n_cells * (x[1]-x[0])
        out[f"{pct}%"] = dict(n_cells=n_cells, length_m=float(length), pct=pct)
    return out

# Main
if __name__ == "__main__":
    # Load cycles for 118-128 window, we will use snapshot at rel 123° (dominant sensor phase)
    # Choose rel_phase 123°
    rel = 123.0
    # For each N, get last 3 pairs
    N_list = [250,300,350,400]
    all_data = {}
    for N in N_list:
        # Load cycles 36-40 as before
        base = None
        if N==250:
            cont = Path("results/p4-r8-20260922/artifacts")
            paths = [cont/f"N250-continuation-cycle{i:02}.json.gz" for i in range(36,41)]
        elif N==300:
            cont = Path("results/p4-r8-20260922/artifacts")
            paths = [cont/f"N300-continuation-cycle{i:02}.json.gz" for i in range(36,41)]
        elif N==350:
            base = Path("results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles")
            paths = [base/f"G1-cycle{i:02}.json.gz" for i in range(36,41)]
        elif N==400:
            base = Path("results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles")
            paths = [base/f"G1-cycle{i:02}.json.gz" for i in range(36,41)]
        rows = [load_cycle(p) for p in paths if p.exists()]
        print(f"N{N} loaded {len(rows)}")
        # For each pair 40vs38 etc.
        x_centers, volumes, dx, n = get_mesh_centers(N)
        # Store
        pairs = []
        for offset in [0,1,2]: # 40vs38,39vs37,38vs36
            if len(rows) < 3+offset:
                continue
            cur = rows[-(1+offset)]
            prev = rows[-(3+offset)]
            # Find snapshots at rel 123
            snap_cur = find_snapshot_for_phase(cur, rel)
            snap_prev = find_snapshot_for_phase(prev, rel)
            p_cur, rho_cur, u_cur, T_cur, Y_cur, prim_cur = extract_p_rho_u_T_Y(snap_cur)
            p_prev, rho_prev, u_prev, T_prev, Y_prev, prim_prev = extract_p_rho_u_T_Y(snap_prev)
            # Detect fronts
            front_cur = detect_front(p_cur, x_centers, dx)
            front_prev = detect_front(p_prev, x_centers, dx)
            delta_x = front_cur['x_front'] - front_prev['x_front']
            delta_x_dx = delta_x/dx if dx else 0
            # Spatial error total
            err_p = spatial_error(p_prev, p_cur, x_centers, dx)
            err_rho = spatial_error(rho_prev, rho_cur, x_centers, dx)
            err_u = spatial_error(u_prev, u_cur, x_centers, dx)
            # Error outside front (1,2,3 cells)
            radii = [dx*1, dx*2, dx*3]
            outside = error_outside_front(p_prev, p_cur, x_centers, front_cur, radii)
            support = support_fraction(p_prev, p_cur, x_centers)
            # Conservative variables: rho, rho*u, rho*E, rho*Y
            # Compute rho*E = p/(gamma-1)+0.5*rho*u^2
            gamma=1.35
            E_cur = p_cur/(gamma-1)+0.5*rho_cur*u_cur*u_cur
            E_prev = p_prev/(gamma-1)+0.5*rho_prev*u_prev*u_prev
            rhoE_cur = rho_cur*E_cur # actually primitive already includes? Wait primitive is rho,u,p,Y, so rho*E = E*rho? But E is energy per mass? Let's compute total energy per volume?
            # For conservative, rhoE = p/(gamma-1)+0.5*rho*u^2  (energy per volume)
            rhoE_cur = p_cur/(gamma-1)+0.5*rho_cur*u_cur*u_cur
            rhoE_prev = p_prev/(gamma-1)+0.5*rho_prev*u_prev*u_prev
            # Actually that's E*? Use same
            err_rhoE = spatial_error(rhoE_prev, rhoE_cur, x_centers, dx)
            # Sensor relation: x_front vs sensor x 0.10
            sensor_x = 0.10
            front_cross = abs(front_cur['x_front']-sensor_x) < front_cur['width_m']/2
            # Orbit AB vs lag2: need to compute AB difference for same N (e.g., 40vs39 is A/B)
            # For lag2 we already have 40vs38, for AB we can compute 40vs39
            # Do AB for last pair
            prev_ab = rows[-2] # 39
            cur_ab = rows[-1] # 40
            snap_ab_prev = find_snapshot_for_phase(prev_ab, rel)
            snap_ab_cur = find_snapshot_for_phase(cur_ab, rel)
            p_ab_prev,_rho,_u,_T,_Y,_ = extract_p_rho_u_T_Y(snap_ab_prev)
            p_ab_cur,_,_,_,_,_ = extract_p_rho_u_T_Y(snap_ab_cur)
            err_ab = spatial_error(p_ab_prev, p_ab_cur, x_centers, dx)
            # Also need lag2 for both parities: we already have 3 pairs covering odd/even
            pairs.append(dict(
                pair=f"{len(rows)-offset} vs {len(rows)-2-offset}",
                rel_phase=rel,
                front_cur=front_cur,
                front_prev=front_prev,
                delta_x=delta_x,
                delta_x_dx=delta_x_dx,
                delta_p_left=front_cur['p_left']-front_prev['p_left'],
                delta_p_right=front_cur['p_right']-front_prev['p_right'],
                delta_jump=front_cur['jump']-front_prev['jump'],
                delta_width=front_cur['width_m']-front_prev['width_m'],
                err_p=err_p,
                err_rho=err_rho,
                err_u=err_u,
                err_rhoE=err_rhoE,
                outside=outside,
                support=support,
                sensor_front=dict(sensor_x=sensor_x, front_x=front_cur['x_front'], width=front_cur['width_m'], cross=front_cross, dist=abs(front_cur['x_front']-sensor_x)),
                err_ab=err_ab,
                # For conservative also check
            ))
        all_data[str(N)] = dict(
            dx=dx, n=n, x_centers=x_centers.tolist()[:5], # sample
            pairs=pairs,
            # Also need to store for context 100-150 we could do but not needed
        )
        print(f"N{N} pairs {len(pairs)} delta_x_avg {sum(p['delta_x'] for p in pairs)/len(pairs):.5f} m")
    # Save
    # Need to make serializable: convert np arrays already handled
    import json
    # For front_tracking, save front positions
    front_tracking = {}
    for N in all_data:
        front_tracking[N] = [dict(pair=p['pair'], x_front_cur=p['front_cur']['x_front'], x_front_prev=p['front_prev']['x_front'], delta_x=p['delta_x'], delta_x_dx=p['delta_x_dx'], p_left_cur=p['front_cur']['p_left'], p_right_cur=p['front_cur']['p_right'], jump_cur=p['front_cur']['jump'], width_m_cur=p['front_cur']['width_m'], width_cells_cur=p['front_cur']['width_cells']) for p in all_data[N]['pairs']]
    (RESULT/"front_tracking.json").write_text(json.dumps(front_tracking, indent=2))
    # spatial_error
    spatial_error_out = {}
    for N in all_data:
        spatial_error_out[N] = [dict(pair=p['pair'], err_p=p['err_p'], err_rho=p['err_rho'], err_u=p['err_u'], outside=p['outside'], support=p['support']) for p in all_data[N]['pairs']]
    (RESULT/"spatial_error.json").write_text(json.dumps(spatial_error_out, indent=2))
    # mesh_trend
    mesh_trend = {}
    for N in N_list:
        key=str(N)
        dx = all_data[key]['dx']
        # avg front width
        widths = [p['front_cur']['width_m'] for p in all_data[key]['pairs']]
        widths_c = [p['front_cur']['width_cells'] for p in all_data[key]['pairs']]
        delta_xs = [p['delta_x'] for p in all_data[key]['pairs']]
        delta_dx = [p['delta_x_dx'] for p in all_data[key]['pairs']]
        jumps = [p['front_cur']['jump'] for p in all_data[key]['pairs']]
        lag2_L2 = [p['err_p']['L2'] for p in all_data[key]['pairs']]
        lag2_outside = [p['outside'][f"r_{dx*3:.4f}"]['L2'] if p['outside'][f"r_{dx*3:.4f}"] else 0 for p in all_data[key]['pairs']]
        support90 = [p['support']['90%']['length_m'] for p in all_data[key]['pairs']]
        mesh_trend[key] = dict(
            dx=dx, n=N,
            front_width_m=sum(widths)/len(widths),
            front_width_cells=sum(widths_c)/len(widths_c),
            delta_x_m=sum(delta_xs)/len(delta_xs),
            delta_x_dx=sum(delta_dx)/len(delta_dx),
            jump_strength=sum(jumps)/len(jumps),
            lag2_L2_total=sum(lag2_L2)/len(lag2_L2),
            lag2_L2_outside_3cells=sum(lag2_outside)/len(lag2_outside),
            error_support_90_m=sum(support90)/len(support90),
            error_support_90_cells=sum([p['support']['90%']['n_cells'] for p in all_data[key]['pairs']])/len(all_data[key]['pairs'])
        )
    (RESULT/"mesh_trend.json").write_text(json.dumps(mesh_trend, indent=2))
    # sensor_front relation
    sensor_front = {}
    for N in all_data:
        sensor_front[N] = [dict(pair=p['pair'], sensor_x=p['sensor_front']['sensor_x'], front_x=p['sensor_front']['front_x'], width=p['sensor_front']['width'], cross=p['sensor_front']['cross'], dist=p['sensor_front']['dist']) for p in all_data[N]['pairs']]
    (RESULT/"sensor_front_relation.json").write_text(json.dumps(sensor_front, indent=2))
    # orbit AB vs lag2
    orbit = {}
    for N in all_data:
        # For last lag2 pair 40vs38 and AB 40vs39
        # Use first pair (40vs38) lag2 and AB from last two cycles (40vs39)
        # We already computed err_ab for each pair's AB? Actually err_ab in pairs is for that pair's AB? No, we computed AB as 40vs39 for each pair? That's not correct, we computed AB as rows[-1] vs rows[-2] for each pair but reused same AB for all pairs. Let's compute properly: AB is 40vs39,39vs38,38vs37 etc., but we can compute directly from rows
        # Simplify: compute AB for last 3 AB pairs
        rows = [load_cycle(p) for p in [Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{i:02}.json.gz") for i in range(38,41)] ] if N==350 else []
        # For generic, just use err_ab from first pair (which is AB 40vs39)
        if all_data[N]['pairs']:
            ab = all_data[N]['pairs'][0]['err_ab']
            lag2 = all_data[N]['pairs'][0]['err_p']
            orbit[N] = dict(AB_L2=ab['L2'], AB_max=ab['max_abs'], lag2_L2=lag2['L2'], lag2_max=lag2['max_abs'], ratio_L2=ab['L2']/lag2['L2'] if lag2['L2'] else 0)
    (RESULT/"orbit_ab_vs_lag2.json").write_text(json.dumps(orbit, indent=2))
    print("Done spatial")
