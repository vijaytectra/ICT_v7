"""Unicorn v5 - the sweep itself made fully parametric, because that is the one rule
where the three sources disagree and where v2 and v3/v4 sat at opposite extremes.

  v2      low < level                                     (that is a BOS, not a sweep)
  v3/v4   low < level AND close > level AND wick > 60%     all on ONE candle

SrsBlack 02-liquidity/liquidity-sweep.md actually says the reversal comes
"on the same OR FOLLOWING candle", and allows "close to it without sustaining the
break". v3/v4 only ever allowed the same candle - too strict in the other direction.

Parameters
  reclaim_bars  0 = no reclaim required (v2)     1 = same candle (v3/v4)     k = within k bars
  wick_frac     0.0 = no wick test               0.6 = the quantified rule
  pool          'swing'  any confirmed swing low/high (minor pivot)
                'equal'  relative equal lows/highs - a real resting pool
                'session' prior-session extreme
  pool_n        swing lookback used to define the pool (bigger = more significant)
"""
import numpy as np
from models.unicorn_v4 import _ob_at


def swings(h, l, n):
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        if h[i-n:i+n+1].argmax() == n: hi[i+n] = True; hp[i+n] = h[i]
        if l[i-n:i+n+1].argmin() == n: lo[i+n] = True; lp[i+n] = l[i]
    return hi, hp, lo, lp


def _pools(hp, lp, hi, lo, mode, tol):
    """Turn the confirmed swing series into the pool levels a sweep may target."""
    if mode == "swing":
        return hp, lp
    ph = np.full(len(hp), np.nan); pl = np.full(len(lp), np.nan)
    rh, rl = [], []
    for i in range(len(hp)):
        if hi[i]: rh.append((i, hp[i]))
        if lo[i]: rl.append((i, lp[i]))
        # equal highs/lows: two swings within tol -> a real resting pool
        if len(rh) >= 2 and abs(rh[-1][1] - rh[-2][1]) <= tol: ph[i] = max(rh[-1][1], rh[-2][1])
        elif i and np.isfinite(ph[i-1]): ph[i] = ph[i-1]
        if len(rl) >= 2 and abs(rl[-1][1] - rl[-2][1]) <= tol: pl[i] = min(rl[-1][1], rl[-2][1])
        elif i and np.isfinite(pl[i-1]): pl[i] = pl[i-1]
    return ph, pl


def detect(o, h, l, c, atr, n=3, pool_n=None, max_gap=60, disp_ratio=0.5,
           wick_frac=0.6, reclaim_bars=1, pool="swing", eq_tol=0.0,
           ob_back=30, nested=False, pd_lookback=60):
    N = len(c)
    pool_n = pool_n or n
    hi, hp, lo, lp = swings(h, l, n)                       # for the OB anchor
    Hi, Hp, Lo, Lp = swings(h, l, pool_n)                  # for the liquidity pool
    tol = eq_tol if eq_tol > 0 else np.nanmedian(atr[np.isfinite(atr)]) * 0.25
    PH, PL = _pools(Hp, Lp, Hi, Lo, pool, tol)

    rng_hi = np.full(N, np.nan); rng_lo = np.full(N, np.nan)
    for i in range(pd_lookback, N):
        rng_hi[i] = h[i-pd_lookback:i].max(); rng_lo[i] = l[i-pd_lookback:i].min()

    out = []
    sh_bar = sl_bar = -1
    lvl_lo = lvl_hi = np.nan
    pend_lo = pend_hi = None        # (start_bar, level, extreme) awaiting reclaim
    s_lo_i = s_hi_i = -1; s_lo_px = s_hi_px = np.nan
    ob_bull = ob_bear = None

    for i in range(max(n, pool_n) + 3, N):
        if hi[i]: sh_bar = i - n
        if lo[i]: sl_bar = i - n
        if np.isfinite(PH[i]): lvl_hi = PH[i]
        if np.isfinite(PL[i]): lvl_lo = PL[i]

        if s_lo_i >= 0 and i - s_lo_i > max_gap: s_lo_i, s_lo_px, ob_bull = -1, np.nan, None
        if s_hi_i >= 0 and i - s_hi_i > max_gap: s_hi_i, s_hi_px, ob_bear = -1, np.nan, None

        rng_i = max(h[i] - l[i], 1e-12)

        # ---------- SELL-SIDE RAID -> arms a bullish setup ----------
        if np.isfinite(lvl_lo) and l[i] < lvl_lo:
            if reclaim_bars == 0:                                   # v2 behaviour
                if sh_bar > 0 and (s_lo_i < 0 or l[i] < s_lo_px):
                    ob = _ob_at(o, c, sh_bar, True, ob_back)
                    if ob: s_lo_i, s_lo_px, ob_bull = i, l[i], (ob[0], ob[1])
            elif pend_lo is None or l[i] < pend_lo[2]:
                pend_lo = (i, lvl_lo, l[i])
        if pend_lo is not None:
            b0, lv, ext = pend_lo
            if i - b0 >= reclaim_bars:                              # window closed
                pend_lo = None
            elif c[i] > lv and (c[i] - l[i]) > wick_frac * rng_i:   # reclaimed
                if sh_bar > 0 and (s_lo_i < 0 or ext < s_lo_px):
                    ob = _ob_at(o, c, sh_bar, True, ob_back)
                    if ob: s_lo_i, s_lo_px, ob_bull = i, ext, (ob[0], ob[1])
                pend_lo = None

        # ---------- BUY-SIDE RAID -> arms a bearish setup ----------
        if np.isfinite(lvl_hi) and h[i] > lvl_hi:
            if reclaim_bars == 0:
                if sl_bar > 0 and (s_hi_i < 0 or h[i] > s_hi_px):
                    ob = _ob_at(o, c, sl_bar, False, ob_back)
                    if ob: s_hi_i, s_hi_px, ob_bear = i, h[i], (ob[0], ob[1])
            elif pend_hi is None or h[i] > pend_hi[2]:
                pend_hi = (i, lvl_hi, h[i])
        if pend_hi is not None:
            b0, lv, ext = pend_hi
            if i - b0 >= reclaim_bars: pend_hi = None
            elif c[i] < lv and (h[i] - c[i]) > wick_frac * rng_i:
                if sl_bar > 0 and (s_hi_i < 0 or ext > s_hi_px):
                    ob = _ob_at(o, c, sl_bar, False, ob_back)
                    if ob: s_hi_i, s_hi_px, ob_bear = i, ext, (ob[0], ob[1])
                pend_hi = None

        if np.isnan(atr[i]) or atr[i] <= 0: continue
        body = abs(c[i] - o[i])
        if body / rng_i < disp_ratio: continue

        for side in (1, -1):
            sw_i, sw_px, ob = ((s_lo_i, s_lo_px, ob_bull) if side == 1
                               else (s_hi_i, s_hi_px, ob_bear))
            if not (sw_i > 0 and ob and 0 < i - sw_i <= max_gap): continue
            b_lo, b_hi = ob
            if side == 1 and not (c[i] > b_hi and c[i] > o[i]): continue
            if side == -1 and not (c[i] < b_lo and c[i] < o[i]): continue
            found = None
            for k in range(sw_i + 2, i + 1):
                if side == 1 and l[k] > h[k-2]: g_lo, g_hi = h[k-2], l[k]
                elif side == -1 and h[k] < l[k-2]: g_lo, g_hi = h[k], l[k-2]
                else: continue
                if nested and not (g_lo >= b_lo and g_hi <= b_hi): continue
                z = (max(g_lo, b_lo), min(g_hi, b_hi))
                if z[1] > z[0]: found = z; break
            if found:
                out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                                sweep_px=sw_px, sweep_bar=sw_i, brk_lo=b_lo, brk_hi=b_hi,
                                mt=(b_lo + b_hi) / 2, mss_origin=b_lo if side == 1 else b_hi,
                                leg_lo=min(l[sw_i:i+1].min(), sw_px), leg_hi=h[sw_i:i+1].max(),
                                rng_lo=rng_lo[i], rng_hi=rng_hi[i], d_body_ratio=body / rng_i,
                                d_opp_wick=0.0, d_body_avg=1.0,
                                d_fvg_w=(found[1]-found[0]) / atr[i], sh_hist=[], sl_hist=[]))
            if side == 1: s_lo_i, ob_bull = -1, None
            else: s_hi_i, ob_bear = -1, None
    return out
