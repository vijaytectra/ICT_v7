"""Unicorn v2 — every rule in models/SPEC.md exposed as a switch, so each one can be
measured instead of assumed. (v1 postmortem mistake #5: "assumed confirmations help",
when sweep/MSS measured anti-predictive.)"""
import numpy as np

def swings(h, l, n):
    N = len(h); hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        if h[i-n:i+n+1].argmax() == n: hi[i+n] = True; hp[i+n] = h[i]
        if l[i-n:i+n+1].argmin() == n: lo[i+n] = True; lp[i+n] = l[i]
    return hi, hp, lo, lp

def _brk_zone(o, c, h, l, start, end, want_down, use_body, brk_all=False):
    j = end - 1
    while j >= start and ((c[j] < o[j]) != want_down): j -= 1
    if j < start: return None
    if brk_all:                       # "the SERIES of down-close candles" - widest reading
        idx = [x for x in range(start, end) if (c[x] < o[x]) == want_down]
        k = idx[0]
    else:                             # last consecutive run only
        k = j
        while k - 1 >= start and ((c[k-1] < o[k-1]) == want_down): k -= 1
    if use_body:                                    # R7 brodenbeck reading
        a = np.minimum(o[k:j+1], c[k:j+1]).min(); b = np.maximum(o[k:j+1], c[k:j+1]).max()
    else:                                           # R7 OpenMobius reading (wicks)
        a = l[k:j+1].min(); b = h[k:j+1].max()
    return a, b, k

def detect(o, h, l, c, atr, n=3, max_gap=30, disp_atr=0.0, disp_ratio=0.0,
           leg_atr=0.0, use_body=False, brk_all=False, pd_lookback=60,
           major_n=0):
    """major_n > 0 requires the raid to take out a MAJOR pool: the sweep bar must
    print the lowest low (highest high) of the preceding `major_n` bars, not merely
    dip under the last minor swing. This is the distinction the sources draw between
    a real draw on liquidity and any small swing point."""
    N = len(c); hi, hp, lo, lp = swings(h, l, n)
    rng_hi = np.full(N, np.nan); rng_lo = np.full(N, np.nan)
    for i in range(pd_lookback, N):                 # R10 dealing range
        rng_hi[i] = h[i-pd_lookback:i].max(); rng_lo[i] = l[i-pd_lookback:i].min()
    out = []
    sh_hist, sl_hist = [], []          # confirmed swing levels, for liquidity targets
    sh = sl = np.nan
    s_lo_i = s_hi_i = -1; s_lo_px = s_hi_px = np.nan; sh_ref = sl_ref = np.nan
    for i in range(n + 3, N):
        if hi[i]: sh = hp[i]; sh_hist.append(hp[i])
        if lo[i]: sl = lp[i]; sl_hist.append(lp[i])
        # R3 timeout - "state resets if MSS doesn't follow the sweep within
        # max_bars_sweep_to_mss" (entry-sequence.md). Without this reset a latched
        # sweep can only be replaced by an even deeper one, so after the sample's
        # extreme the detector goes permanently silent.
        if s_lo_i >= 0 and i - s_lo_i > max_gap: s_lo_i, s_lo_px = -1, np.nan
        if s_hi_i >= 0 and i - s_hi_i > max_gap: s_hi_i, s_hi_px = -1, np.nan

        maj_lo = maj_hi = True
        if major_n > 0:
            if i < major_n:
                maj_lo = maj_hi = False
            else:
                maj_lo = l[i] <= l[i-major_n:i].min()
                maj_hi = h[i] >= h[i-major_n:i].max()

        if maj_lo and not np.isnan(sl) and l[i] < sl and (s_lo_i < 0 or l[i] < s_lo_px):
            s_lo_i, s_lo_px, sh_ref = i, l[i], sh          # R1 + R2 freeze
        if maj_hi and not np.isnan(sh) and h[i] > sh and (s_hi_i < 0 or h[i] > s_hi_px):
            s_hi_i, s_hi_px, sl_ref = i, h[i], sl
        if np.isnan(atr[i]) or atr[i] <= 0: continue
        body = abs(c[i] - o[i]); rng = max(h[i] - l[i], 1e-12)
        ok_disp = body >= disp_atr * atr[i] and body / rng >= disp_ratio   # R4

        for side in (1, -1):
            if side == 1:
                sw_i, sw_px, ref = s_lo_i, s_lo_px, sh_ref
                mss = (not np.isnan(ref)) and c[i] > ref and c[i] > o[i]
            else:
                sw_i, sw_px, ref = s_hi_i, s_hi_px, sl_ref
                mss = (not np.isnan(ref)) and c[i] < ref and c[i] < o[i]
            if not (sw_i > 0 and 0 < i - sw_i <= max_gap and mss and ok_disp):  # R3
                continue
            if leg_atr > 0 and abs(c[i] - sw_px) < leg_atr * atr[i]:   # R4 leg-level
                continue
            bz = _brk_zone(o, c, h, l, sw_i, i, side == 1, use_body, brk_all)            # R7
            if bz is None: continue
            b_lo, b_hi, b_k = bz
            found = None
            for k in range(sw_i + 2, i + 1):                                    # R6
                if side == 1 and l[k] > h[k-2]:
                    z = (max(h[k-2], b_lo), min(l[k], b_hi))
                elif side == -1 and h[k] < l[k-2]:
                    z = (max(h[k], b_lo), min(l[k-2], b_hi))
                else: continue
                if z[1] > z[0]: found = z; break                                # R8
            if found:
                leg_lo = min(l[sw_i:i+1].min(), sw_px); leg_hi = h[sw_i:i+1].max()
                opp = (h[i] - max(o[i], c[i])) if side == 1 else (min(o[i], c[i]) - l[i])
                avgb = np.nanmean(np.abs(c[max(0, i-20):i] - o[max(0, i-20):i])) or 1e-12
                out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                                sweep_px=sw_px, sweep_bar=sw_i,
                                mss_origin=(l[b_k] if side == 1 else h[b_k]),
                                brk_lo=b_lo, brk_hi=b_hi,
                                leg_lo=leg_lo, leg_hi=leg_hi,
                                rng_lo=rng_lo[i], rng_hi=rng_hi[i],
                                d_body_ratio=body / rng, d_opp_wick=opp / rng,
                                d_body_avg=body / avgb, d_fvg_w=(found[1] - found[0]) / atr[i],
                                sh_hist=list(sh_hist[-40:]), sl_hist=list(sl_hist[-40:])))
            if side == 1: s_lo_i = -1
            else: s_hi_i = -1
    return out
