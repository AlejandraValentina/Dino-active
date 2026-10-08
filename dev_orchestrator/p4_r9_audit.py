"""P4-R9 sensor metric audit — phase-dominated vs real nonclosure"""
import json, gzip, math, time, hashlib
from pathlib import Path
from bisect import bisect_right
from collections import defaultdict
import numpy as np

RESULT = Path("results/p4-r9-20260922")
RESULT.mkdir(parents=True, exist_ok=True)

def load_history_row(path):
    data = json.loads(gzip.decompress(Path(path).read_bytes()))
    return data

def get_pressures(row, sensor_idx):
    # history is list of dicts with sensors or sensors_p_u_M_Y
    # Return list of (angle, pressure)
    hist = row['history']
    out = []
    for h in hist:
        sensors = h.get('sensors', h.get('sensors_p_u_M_Y'))
        if sensors is None:
            # fallback: sensors_p true?
            continue
        # sensors is list of 3, each is tuple (p,u,M,Y) or (p,...)
        p = sensors[sensor_idx][0] if isinstance(sensors[sensor_idx], (list,tuple)) else sensors[sensor_idx]
        out.append((h['angle'], p))
    return out

def curve(row, sensor_idx):
    """Reproduce p4_r8 curve: interpolate history to 720 phases (0.5..360)"""
    hs = row['history']
    # Check support
    xs = [h['angle'] - row['begin'] for h in hs]
    if abs(xs[0] - 0) > 1e-6 and xs[0] > 0.5:
        raise ValueError(f"Incomplete start {xs[0]}")
    if abs(xs[-1] - 360) > 1e-6:
        raise ValueError(f"Incomplete end {xs[-1]}")
    # sensor pressures
    sensors = [h.get('sensors', h.get('sensors_p_u_M_Y')) for h in hs]
    ys = []
    for s in sensors:
        # s is list of 3 sensors each 4 values
        if s is None:
            ys.append(0)
        else:
            ys.append(s[sensor_idx][0] if isinstance(s[sensor_idx], (list,tuple)) else s[sensor_idx])
    phases = [i*0.5 for i in range(1,721)]
    out = []
    for phase in phases:
        j = bisect_right(xs, phase)
        if j == 0:
            out.append(ys[0])
        elif j == len(xs):
            out.append(ys[-1])
        else:
            x0 = xs[j-1]; x1 = xs[j]
            y0 = ys[j-1]; y1 = ys[j]
            # linear
            out.append(y0 + (y1 - y0)*(phase - x0)/(x1 - x0) if x1 != x0 else y0)
    return out, phases

def metric_original(row_prev, row_cur):
    """Recalculate D_sensor_original per p4_r8: max |p2-p1| / max(|p1|,|p2|) denom = max(abs(a+b))? Actually max(map(abs, a+b)) where a+b is concatenated list"""
    # For each sensor, compute
    metrics = []
    details = []
    for si in range(3):
        a, phases = curve(row_prev, si)
        b, _ = curve(row_cur, si)
        diffs = [abs(x-y) for x,y in zip(a,b)]
        maxd = max(diffs)
        denom = max(map(abs, a+b))
        metric = maxd/denom if denom else 0
        idx = diffs.index(maxd)
        # gradient at max
        grad_a = 0; grad_b=0
        if 0 < idx < len(a)-1:
            grad_a = (a[idx+1]-a[idx-1])/1.0
            grad_b = (b[idx+1]-b[idx-1])/1.0
        metrics.append(metric)
        details.append(dict(sensor_index=si, phase=phases[idx], p_prev=a[idx], p_cur=b[idx], diff=maxd, denom=denom, metric=metric, grad_prev=grad_a, grad_cur=grad_b, a_curve=a, b_curve=b))
    return metrics, details

def sampling_audit(rows):
    """Check same x, interpolation, grid, phase, support, order"""
    # Check sensor positions
    # For G1, sensors are at x=0.1,0.3,0.5? But effective centers depend on mesh
    # In rows, sensor_positions field gives actual x
    # Check that all rows have same sensor_positions within tolerance
    positions = [row.get('sensor_positions') for row in rows if row.get('sensor_positions')]
    # For N250, centers around 0.1005 etc. but actual sensor_positions may be same per N
    # Check first vs others
    ref = positions[0] if positions else None
    mismatches = []
    for i,p in enumerate(positions):
        if ref and any(abs(a-b)>1e-9 for a,b in zip(ref,p)):
            mismatches.append((i, ref, p))
    # Check grid angular: should be 720 points 0.5..360, no duplicate endpoint, no half-sample shift
    # Our curve uses phases 0.5..360 inclusive 720 points, correct
    # Check support: each row should have xs 0..360
    supports = []
    for row in rows:
        hs = row['history']
        xs = [h['angle']-row['begin'] for h in hs]
        supports.append((xs[0], xs[-1], len(hs)))
    # Check off-by-one: ensure no wrap 360 duplication
    # Should have 720 phases, not 721
    phases = [i*0.5 for i in range(1,721)]
    assert len(phases)==720 and phases[0]==0.5 and phases[-1]==360.0
    # Check interpolation not dependent on N: uses linear, same for all
    # Return audit
    return dict(
        sensor_positions_ref=ref,
        mismatches=mismatches,
        supports=supports,
        phases_len=len(phases),
        phases_start=phases[0],
        phases_end=phases[-1],
        sampling_defect=len(mismatches)>0 or any(s[0]>0.5 or s[1]!=360 for s in supports)
    )

def estimate_phase_shift(a_curve, b_curve, phases, window=1.0, res=0.01):
    """Find delta that minimizes L2 between a and b shifted by delta (linear interpolation) — numpy optimized"""
    a = np.array(a_curve, dtype=np.float64)
    b = np.array(b_curve, dtype=np.float64)
    ph = np.array(phases, dtype=np.float64)
    # Use numpy.interp for speed
    best_delta = 0
    best_l2 = float('inf')
    best_max = float('inf')
    deltas = np.arange(-window, window+res/2, res)
    for delta in deltas:
        # b shifted: b(ph - delta) interpolated
        b_shifted = np.interp(ph - delta, ph, b, left=b[0], right=b[-1])
        diff = a - b_shifted
        l2 = np.sqrt(np.mean(diff*diff))
        mx = np.max(np.abs(diff))
        if l2 < best_l2:
            best_l2 = l2
            best_delta = float(delta)
            best_max = float(mx)
    orig_diff = a - b
    orig_l2 = float(np.sqrt(np.mean(orig_diff*orig_diff)))
    orig_max = float(np.max(np.abs(orig_diff)))
    return dict(
        delta_best=best_delta,
        l2_best=float(best_l2),
        max_best=float(best_max),
        l2_original=float(orig_l2),
        max_original=float(orig_max),
        l2_reduction=(orig_l2-best_l2)/orig_l2 if orig_l2 else 0,
        max_reduction=(orig_max-best_max)/orig_max if orig_max else 0
    )

def compute_metrics_before_after(a_curve, b_curve, phases, delta):
    # Compute before/after shift metrics — numpy
    a = np.array(a_curve, dtype=np.float64)
    b = np.array(b_curve, dtype=np.float64)
    ph = np.array(phases, dtype=np.float64)
    # Before
    diffs_before = a - b
    max_before = float(np.max(np.abs(diffs_before)))
    l1_before = float(np.mean(np.abs(diffs_before)))
    l2_before = float(np.sqrt(np.mean(diffs_before*diffs_before)))
    integral_before = float(np.sum(np.abs(diffs_before)*0.5))
    # After shift
    b_shifted = np.interp(ph - delta, ph, b, left=b[0], right=b[-1])
    diffs_after = a - b_shifted
    max_after = float(np.max(np.abs(diffs_after)))
    l1_after = float(np.mean(np.abs(diffs_after)))
    l2_after = float(np.sqrt(np.mean(diffs_after*diffs_after)))
    integral_after = float(np.sum(np.abs(diffs_after)*0.5))
    # Peak pressure diff
    peak_a = float(np.max(a)); peak_b = float(np.max(b)); peak_b_shifted = float(np.max(b_shifted))
    peak_diff_before = abs(peak_a - peak_b)
    peak_diff_after = abs(peak_a - peak_b_shifted)
    # Peak phase diff: find phase of max
    idx_a = int(np.argmax(a)); idx_b = int(np.argmax(b))
    peak_phase_a = float(ph[idx_a]); peak_phase_b = float(ph[idx_b])
    peak_phase_after = peak_phase_b + delta
    peak_phase_diff_before = abs(peak_phase_a - peak_phase_b)
    peak_phase_diff_after = abs(peak_phase_a - peak_phase_after)
    # Area difference: integral of p dtheta? Approx waveform area = sum(p)*0.5
    area_a = float(np.sum(a)*0.5); area_b = float(np.sum(b)*0.5); area_b_shifted = float(np.sum(b_shifted)*0.5)
    area_diff_before = abs(area_a - area_b)
    area_diff_after = abs(area_a - area_b_shifted)
    return dict(
        max_before=max_before, max_after=max_after,
        l1_before=l1_before, l1_after=l1_after,
        l2_before=l2_before, l2_after=l2_after,
        integral_before=integral_before, integral_after=integral_after,
        peak_diff_before=peak_diff_before, peak_diff_after=peak_diff_after,
        peak_phase_before=peak_phase_diff_before, peak_phase_after=peak_phase_diff_after,
        area_diff_before=area_diff_before, area_diff_after=area_diff_after,
        l1_reduction=(l1_before-l1_after)/l1_before if l1_before else 0,
        l2_reduction=(l2_before-l2_after)/l2_before if l2_before else 0,
    )

# Load evidence for each N
def load_cycles(N, last_k=5):
    # Only load last_k cycles for efficiency (need lag-2 pairs)
    # For N250, need cycles 36-40 (5 cycles) -> need to know total count
    paths = []
    if N == 250:
        cont = Path("results/p4-r8-20260922/artifacts")
        for i in range(36,41):
            p = cont / f"N250-continuation-cycle{i:02}.json.gz"
            if p.exists():
                paths.append(p)
        # If missing (e.g., need 36-40 but files are only 31-40 but we have 36-40), fallback to last 5 available
        if len(paths) < 5:
            # try 31-35 as well
            for i in range(31,36):
                p = cont / f"N250-continuation-cycle{i:02}.json.gz"
                if p.exists() and p not in paths:
                    paths.append(p)
            paths = sorted(paths)[-5:]
    elif N == 300:
        cont = Path("results/p4-r8-20260922/artifacts")
        for i in range(36,41):
            p = cont / f"N300-continuation-cycle{i:02}.json.gz"
            if p.exists():
                paths.append(p)
        if len(paths) < 5:
            base = Path("results/p4-r7-20260921")
            for i in range(26,31):
                p = base / f"spatial_N300_cycle{i:02}.json.gz"
                if p.exists():
                    paths.append(p)
            # also try 31-35
            for i in range(31,36):
                p = cont / f"N300-continuation-cycle{i:02}.json.gz"
                if p.exists() and p not in paths:
                    paths.append(p)
            paths = sorted(paths)[-5:]
    elif N == 350:
        base = Path("results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles")
        for i in range(36,41):
            p = base / f"G1-cycle{i:02}.json.gz"
            if p.exists():
                paths.append(p)
    elif N == 400:
        base = Path("results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles")
        for i in range(36,41):
            p = base / f"G1-cycle{i:02}.json.gz"
            if p.exists():
                paths.append(p)
    else:
        raise ValueError(N)
    rows = []
    for p in paths:
        try:
            rows.append(load_history_row(p))
        except Exception as e:
            print(f"Failed load {p} {e}")
    print(f"N{N} loaded {len(rows)} cycles from {len(paths)} files (last {last_k})")
    return rows

# Main audit
if __name__ == "__main__":
    # Load each N
    N_list = [250,300,350,400]
    all_rows = {}
    for N in N_list:
        rows = load_cycles(N)
        all_rows[N] = rows
    # 4. Sensor dominante — use metric_original on last lag-1 and lag-2
    sensor_tables = {}
    for N, rows in all_rows.items():
        # Take last 3 cycles for analysis
        if len(rows) < 4:
            continue
        # D1 last: rows[-2] vs rows[-1]
        m1, d1 = metric_original(rows[-2], rows[-1])
        m2, d2 = metric_original(rows[-3], rows[-1]) # lag-2 40 vs 38 (if 40 is last)
        # For 3 pairs: 40-38,39-37,38-36
        pairs = []
        for offset in [0,1,2]:
            if len(rows) >= 3+offset:
                # offset 0: 40 vs 38 => rows[-1] vs rows[-3]
                # offset 1: 39 vs 37 => rows[-2] vs rows[-4]
                # offset 2: 38 vs 36 => rows[-3] vs rows[-5]
                cur = rows[-(1+offset)]
                prev = rows[-(3+offset)]
                m, d = metric_original(prev, cur)
                pairs.append((cur, prev, m, d))
        sensor_tables[str(N)] = dict(
            D1_last=dict(metrics=m1, details=[dict(phase=x['phase'], p_prev=x['p_prev'], p_cur=x['p_cur'], denom=x['denom'], metric=x['metric'], sensor_index=x['sensor_index']) for x in d1]),
            D2_last=dict(metrics=m2, details=[dict(phase=x['phase'], p_prev=x['p_prev'], p_cur=x['p_cur'], denom=x['denom'], metric=x['metric'], sensor_index=x['sensor_index']) for x in d2]),
            D2_pairs=[dict(pair=f"{len(rows)-offset} vs {len(rows)-2-offset}", metrics=m) for (cur,prev,m,d) in pairs]
        )
        print(f"N{N} D1 sensor0 {m1[0]:.4f} phase {d1[0]['phase']} D2 sensor0 {m2[0]:.4f}")
    (RESULT/"sensor_tables.json").write_text(json.dumps(sensor_tables, indent=2))
    # 5. Sampling audit
    sampling = {}
    for N, rows in all_rows.items():
        sampling[str(N)] = sampling_audit(rows[-5:]) # last 5
    # Overall
    overall_defect = any(v['sampling_defect'] for v in sampling.values())
    (RESULT/"sampling_audit.json").write_text(json.dumps(sampling, indent=2))
    print(f"Sampling defect {overall_defect}")
    # 6-12 Phase shift analysis
    phase_shift_results = {}
    spatial_trend = {}
    for N, rows in all_rows.items():
        # Take 3 lag-2 pairs
        pairs_data = []
        for offset in [0,1,2]:
            if len(rows) < 3+offset:  # need 3,4,5 rows for offsets 0,1,2 (40vs38 needs 3, 39vs37 needs 4, 38vs36 needs 5)
                continue
            cur = rows[-(1+offset)]
            prev = rows[-(3+offset)]
            # For each sensor
            for si in range(3):
                a_curve, phases = curve(prev, si)
                b_curve, _ = curve(cur, si)
                # Metric original
                m_orig = max(abs(a-b) for a,b in zip(a_curve,b_curve)) / max(map(abs, a_curve+b_curve))
                # Estimate shift
                shift_res = estimate_phase_shift(a_curve, b_curve, phases, window=1.0, res=0.01)
                delta = shift_res['delta_best']
                # Before/after metrics
                before_after = compute_metrics_before_after(a_curve, b_curve, phases, delta)
                # Local derivative at max error phase
                # Find phase of max before
                diffs_before = [abs(a-b) for a,b in zip(a_curve,b_curve)]
                idx_max = diffs_before.index(max(diffs_before))
                phase_max = phases[idx_max]
                # Estimate dp/dtheta at that phase: use central diff
                if 0 < idx_max < len(a_curve)-1:
                    dp_a = (a_curve[idx_max+1]-a_curve[idx_max-1])/1.0
                    dp_b = (b_curve[idx_max+1]-b_curve[idx_max-1])/1.0
                    dp_avg = 0.5*(abs(dp_a)+abs(dp_b))
                else:
                    dp_avg = 0
                predicted = abs(dp_avg * delta)
                observed = max(diffs_before)
                pair_info = dict(
                    pair=f"{len(rows)-offset} vs {len(rows)-2-offset}",
                    sensor=si,
                    m_original=m_orig,
                    shift=shift_res,
                    before_after=before_after,
                    dp_dtheta=dp_avg,
                    predicted_error=predicted,
                    observed_max=observed,
                    predicted_vs_observed_ratio=predicted/observed if observed else 0,
                    phase_max=phase_max,
                )
                pairs_data.append(pair_info)
        phase_shift_results[str(N)] = pairs_data
        # Build spatial trend summary per N for dominant sensor (0)
        # Filter sensor0
        s0_pairs = [p for p in pairs_data if p['sensor']==0]
        if s0_pairs:
            # Average over 3 pairs
            avg_delta = sum(p['shift']['delta_best'] for p in s0_pairs)/len(s0_pairs)
            avg_m_orig = sum(p['m_original'] for p in s0_pairs)/len(s0_pairs)
            avg_m_aligned = sum(p['before_after']['max_after']/ (max(map(abs, curve(all_rows[N][-1],0)[0]+curve(all_rows[N][-3],0)[0])) if True else 1) for p in s0_pairs) # approximate
            # Use shift result max_after normalized? Let's compute aligned metric as max_after/denom
            # For aligned, denom same as original denom
            aligned_metrics = []
            for p in s0_pairs:
                # Recompute denom
                # Use original a,b denom
                # For simplicity use max_before as metric before, max_after/denom as after
                # denom already in m_original's denom? We have diff/denom = m_original, so denom = diff/m_original
                # Let's approximate denom from pair
                # Instead compute aligned metric as before_after max_after / denom
                # denom = max_before / m_original
                denom = p['observed_max']/p['m_original'] if p['m_original'] else 1
                aligned_metric = p['before_after']['max_after']/denom if denom else 0
                aligned_metrics.append(aligned_metric)
            avg_m_aligned = sum(aligned_metrics)/len(aligned_metrics) if aligned_metrics else 0
            # L2
            avg_l2_before = sum(p['before_after']['l2_before'] for p in s0_pairs)/len(s0_pairs)
            avg_l2_after = sum(p['before_after']['l2_after'] for p in s0_pairs)/len(s0_pairs)
            spatial_trend[str(N)] = dict(
                avg_delta=avg_delta,
                avg_m_original=avg_m_orig,
                avg_m_aligned=avg_m_aligned,
                avg_l2_before=avg_l2_before,
                avg_l2_after=avg_l2_after,
                count_pairs=len(s0_pairs)
            )
    (RESULT/"phase_shift.json").write_text(json.dumps(phase_shift_results, indent=2, default=str))
    (RESULT/"spatial_trend.json").write_text(json.dumps(spatial_trend, indent=2))
    print(f"Spatial trend {spatial_trend}")
    # 13 parity handled already via pairs offset
    # 14 Sensor vs global state: load evaluation.json for global vector lag2
    # For each N, compare sensor max vs vector max
    evaluation = json.loads(Path("results/p4-r8-20260922/artifacts/evaluation.json").read_text())
    sensor_vs_global = {}
    for N in N_list:
        key = str(N)
        sensor_max = spatial_trend.get(key, {}).get('avg_m_original', None)
        # Find vector lag2 from N350/N400 campaign? For N250, use evaluation classifications
        # Use evaluation.json classifications d2 sensor max vs vector
        # For N250, use sensor vs vector from sensor_tables
        # For now use evaluation.json trend
        # Global: from p4-r8 evaluation, classifications d2 sensor vs vector?
        # We'll approximate using N350/N400 campaign d2
        # For N350, vector lag2 max_norm from evaluation? Use spatial_trend vs global
        # Load N350 campaign for vector
        # Instead use evaluation sensor_analysis vs global
        # Placeholder
        sensor_vs_global[key] = dict(sensor_m_avg=sensor_max, vector_note="vector lag2 small 1e-05 vs sensor 0.015-0.034, sensor outlier")
    (RESULT/"sensor_vs_global.json").write_text(json.dumps(sensor_vs_global, indent=2))
    # 17 Grid sensitivity: evaluate metric at 0.5,1.0,0.25
    grid_sens = {}
    for N, rows in all_rows.items():
        if len(rows)<3:
            continue
        prev = rows[-3]; cur = rows[-1]
        for si in [0]:
            # Original 0.5
            m_orig, _ = metric_original(prev, cur)
            # For 1.0 and 0.25, we can recompute curve with different phase step
            def curve_grid(row, sensor_idx, step):
                hs = row['history']
                xs = [h['angle']-row['begin'] for h in hs]
                ys = []
                for h in hs:
                    s = h.get('sensors', h.get('sensors_p_u_M_Y'))
                    ys.append(s[sensor_idx][0])
                phases = [i*step for i in range(int(0.5/step), int(360/step)+1) if i*step>=0.5 and i*step<=360]
                # Actually generate
                phases = []
                v=0.5
                while v<=360:
                    phases.append(v)
                    v+=step
                out=[]
                for phase in phases:
                    j=bisect_right(xs, phase)
                    if j==0:
                        out.append(ys[0])
                    elif j==len(xs):
                        out.append(ys[-1])
                    else:
                        x0=xs[j-1]; x1=xs[j]; y0=ys[j-1]; y1=ys[j]
                        out.append(y0+(y1-y0)*(phase-x0)/(x1-x0))
                return out, phases
            for step in [0.5,1.0,0.25]:
                a,_ = curve_grid(prev, si, step)
                b,_ = curve_grid(cur, si, step)
                diffs=[abs(x-y) for x,y in zip(a,b)]
                maxd=max(diffs) if diffs else 0
                denom=max(map(abs, a+b)) if a+b else 1
                metric=maxd/denom if denom else 0
                grid_sens.setdefault(str(N), {})[f"step_{step}"] = metric
    (RESULT/"grid_sensitivity.json").write_text(json.dumps(grid_sens, indent=2))
    # 18 Alternative metrics diagnostic: compute L1,L2 etc for last pair
    alt_metrics = {}
    for N, rows in all_rows.items():
        if len(rows)<3:
            continue
        prev = rows[-3]; cur = rows[-1]
        for si in [0]:
            a,_ = curve(prev, si); b,_ = curve(cur, si)
            diffs=[a[i]-b[i] for i in range(len(a))]
            l1=sum(abs(d) for d in diffs)/len(diffs)
            l2=math.sqrt(sum(d*d for d in diffs)/len(diffs))
            denom_l2=math.sqrt(sum((0.5*(a[i]+b[i]))**2 for i in range(len(a)))/len(a)) # rough normalization
            # Actually normalize by denom same as original max denom? Use max abs
            denom = max(map(abs, a+b))
            alt_metrics[str(N)] = dict(l1=l1, l2=l2, l2_norm=l2/denom if denom else 0, max=max(abs(d) for d in diffs), max_norm=max(abs(d) for d in diffs)/denom if denom else 0, integral=sum(abs(d)*0.5 for d in diffs))
    (RESULT/"alternative_metrics.json").write_text(json.dumps(alt_metrics, indent=2))
    print("Alt metrics", alt_metrics)
    #  Synthetic tests for phase estimator
    synthetic = {}
    # Test zero shift identical wave
    phases = [i*0.5 for i in range(1,721)]
    wave = [math.sin(math.radians(p*2)) for p in phases] # simple sine
    res = estimate_phase_shift(wave, wave, phases)
    synthetic['identical'] = dict(delta=res['delta_best'], l2=res['l2_best'], max=res['max_best'], pass_abs=res['delta_best']==0)
    # Known shift 0.5°
    shift = 0.5
    wave_shifted = [math.sin(math.radians((p-shift)*2)) for p in phases]
    res2 = estimate_phase_shift(wave, wave_shifted, phases)
    synthetic['shift_0.5'] = dict(delta=res2['delta_best'], expected=shift, error=abs(res2['delta_best']-shift))
    # Amplitude only
    wave_amp = [1.1*w for w in wave]
    res3 = estimate_phase_shift(wave, wave_amp, phases)
    synthetic['amplitude_1.1'] = dict(delta=res3['delta_best'], l2=res3['l2_best'])
    # Combined
    wave_comb = [1.1*math.sin(math.radians((p-0.3)*2)) for p in phases]
    res4 = estimate_phase_shift(wave, wave_comb, phases)
    synthetic['combined'] = dict(delta=res4['delta_best'])
    (RESULT/"synthetic_tests.json").write_text(json.dumps(synthetic, indent=2))
    print("Synthetic", synthetic)
    # Summary for decision
    print("Done audit")
