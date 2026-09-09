"""Unicorn v4 - the breaker polarity and location corrected.

SrsBlack 08-breaker-blocks/bullish-breaker.md:
  "A bullish breaker is a FAILED BEARISH ORDER BLOCK - an originally bearish OB
   (last BULLISH candle before bearish displacement) whose top edge price violated
   by closing above with displacement. The OB body now functions as a bullish
   support zone on retest from above."
  Common mistake, verbatim: "Reversed polarity. A bullish OB doesn't become a
   bullish breaker - it becomes a bearish one."

v2/v3 marked the last DOWN-close run between the sweep and the MSS. That is a bullish
ORDER BLOCK sitting at the sweep low - the exact confusion the sources warn about - and
it sits far below the FVG the displacement leaves, which is why the breaker/FVG overlap
came out under a pip. The breaker belongs at the swing HIGH: the up-close run that began
the decline, which the displacement then closes above.

Bullish sequence (bearish mirrors):
  L1 swing low -> H1 swing high -> sweep L2 below L1 -> displacement closes above the
  bearish OB at H1 -> that OB is now the bullish breaker -> FVG from the displacement
  must overlap it -> entry on the retrace -> stop below L2.
"""
import numpy as np


def swings(h, l, n):
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        if h[i-n:i+n+1].argmax() == n: hi[i+n] = True; hp[i+n] = h[i]
        if l[i-n:i+n+1].argmin() == n: lo[i+n] = True; lp[i+n] = l[i]
    return hi, hp, lo, lp


def _ob_at(o, c, pivot, want_up, back=30):
    """The order block at a swing pivot: the last consecutive run of same-colour
    candles ending at or just before the pivot. Bodies only, combined into ONE block."""
    j = pivot
    while j >= max(pivot - back, 1) and ((c[j] > o[j]) != want_up): j -= 1
    if j < max(pivot - back, 1): return None
    k = j
    while k - 1 >= max(pivot - back, 1) and ((c[k-1] > o[k-1]) == want_up): k -= 1
    lo_ = np.minimum(o[k:j+1], c[k:j+1]).min()
    hi_ = np.maximum(o[k:j+1], c[k:j+1]).max()
    return lo_, hi_, k, j


def detect(o, h, l, c, atr, n=3, max_gap=60, disp_ratio=0.5, wick_frac=0.6,
           strict_sweep=True, ob_back=30, nested=False, pd_lookback=60):
    # nested=True enforces SrsBlack's unicorn criterion c1 literally -
    # "breaker_block + NESTED_FVG": the gap must sit INSIDE the breaker body,
    # not merely intersect its edge.
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n)
    rng_hi = np.full(N, np.nan); rng_lo = np.full(N, np.nan)
    for i in range(pd_lookback, N):
        rng_hi[i] = h[i-pd_lookback:i].max(); rng_lo[i] = l[i-pd_lookback:i].min()

    out = []
    sh = sl = np.nan; sh_bar = sl_bar = -1
    s_lo_i = s_hi_i = -1; s_lo_px = s_hi_px = np.nan
    ob_bull = ob_bear = None                 # (lo, hi) of the OB frozen at the sweep

    for i in range(n + 3, N):
        if hi[i]: sh, sh_bar = hp[i], i - n          # actual pivot bar
        if lo[i]: sl, sl_bar = lp[i], i - n

        if s_lo_i >= 0 and i - s_lo_i > max_gap: s_lo_i, s_lo_px, ob_bull = -1, np.nan, None
        if s_hi_i >= 0 and i - s_hi_i > max_gap: s_hi_i, s_hi_px, ob_bear = -1, np.nan, None

        rng_i = max(h[i] - l[i], 1e-12)

        # --- sweep of sell-side liquidity -> arms a BULLISH setup ---
        if not np.isnan(sl) and l[i] < sl and sh_bar > 0:
            ok = (c[i] > sl and (c[i] - l[i]) > wick_frac * rng_i) if strict_sweep else True
            if ok and (s_lo_i < 0 or l[i] < s_lo_px):
                # the bearish OB at the swing high: last UP-close run before the decline
                ob = _ob_at(o, c, sh_bar, True, ob_back)
                if ob: s_lo_i, s_lo_px, ob_bull = i, l[i], (ob[0], ob[1])
        # --- sweep of buy-side liquidity -> arms a BEARISH setup ---
        if not np.isnan(sh) and h[i] > sh and sl_bar > 0:
            ok = (c[i] < sh and (h[i] - c[i]) > wick_frac * rng_i) if strict_sweep else True
            if ok and (s_hi_i < 0 or h[i] > s_hi_px):
                ob = _ob_at(o, c, sl_bar, False, ob_back)
                if ob: s_hi_i, s_hi_px, ob_bear = i, h[i], (ob[0], ob[1])

        if np.isnan(atr[i]) or atr[i] <= 0: continue
        body = abs(c[i] - o[i])
        if body / rng_i < disp_ratio: continue

        for side in (1, -1):
            sw_i, sw_px, ob = ((s_lo_i, s_lo_px, ob_bull) if side == 1
                               else (s_hi_i, s_hi_px, ob_bear))
            if not (sw_i > 0 and ob and 0 < i - sw_i <= max_gap): continue
            b_lo, b_hi = ob
            # the break: close through the OB body in the new direction, with displacement
            if side == 1 and not (c[i] > b_hi and c[i] > o[i]): continue
            if side == -1 and not (c[i] < b_lo and c[i] < o[i]): continue

            found = None
            for k in range(sw_i + 2, i + 1):
                if side == 1 and l[k] > h[k-2]:
                    g_lo, g_hi = h[k-2], l[k]
                elif side == -1 and h[k] < l[k-2]:
                    g_lo, g_hi = h[k], l[k-2]
                else: continue
                if nested and not (g_lo >= b_lo and g_hi <= b_hi): continue
                z = (max(g_lo, b_lo), min(g_hi, b_hi))
                if z[1] > z[0]: found = z; break
            if found:
                out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                                sweep_px=sw_px, sweep_bar=sw_i,
                                brk_lo=b_lo, brk_hi=b_hi, mt=(b_lo + b_hi) / 2,
                                mss_origin=b_lo if side == 1 else b_hi,
                                leg_lo=min(l[sw_i:i+1].min(), sw_px), leg_hi=h[sw_i:i+1].max(),
                                rng_lo=rng_lo[i], rng_hi=rng_hi[i],
                                d_body_ratio=body / rng_i, d_opp_wick=0.0,
                                d_body_avg=body / max(np.nanmean(np.abs(c[max(0,i-20):i]-o[max(0,i-20):i])), 1e-12),
                                d_fvg_w=(found[1]-found[0]) / atr[i], sh_hist=[], sl_hist=[]))
            if side == 1: s_lo_i, ob_bull = -1, None
            else: s_hi_i, ob_bear = -1, None
    return out
