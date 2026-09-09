"""Unicorn v3 - rebuilt after the v2 sweep-latch bug, with three corrections that
came out of a full re-read of the three reference repositories.

CORRECTION 1 - a sweep is not a break.  SrsBlack 02-liquidity/liquidity-sweep.md:
  "A sweep is distinguished from a break-of-structure by the lack of close beyond the
   swept level - sweep wicks; BOS closes."
      SSL_sweep := low < level AND close > level AND (close-low) > 0.6 * range
  v2 tested only `low < level`, so it fed a reversal model on continuation breaks.

CORRECTION 2 - the block is bodies, combined.  SrsBlack 07-order-blocks/order-block-criteria.md:
  "all three of these candles together is one consecutive candle", "combining both the
   bodies", "the bodies only, not the wicks".

CORRECTION 3 - the displacement must trade through the block's far extreme:
  "this candle trades through the highest of the down candles - so that confirms this
   is a bullish order block".

Retained from v2: MSS must close beyond the swing frozen at sweep time; the FVG must come
from inside the sweep->MSS leg; the overlap must be non-empty; and the R3 timeout resets
the sweep state (the bug that invalidated every v2 number).
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


def _block(o, c, h, l, start, end, want_down):
    """The consecutive same-colour run before the displacement, framed as ONE block.
    Zone spans the COMBINED BODIES; mean threshold is that zone's midpoint."""
    j = end - 1
    while j >= start and ((c[j] < o[j]) != want_down): j -= 1
    if j < start: return None
    k = j
    while k - 1 >= start and ((c[k-1] < o[k-1]) == want_down): k -= 1
    body_lo = np.minimum(o[k:j+1], c[k:j+1]).min()
    body_hi = np.maximum(o[k:j+1], c[k:j+1]).max()
    return body_lo, body_hi, l[k:j+1].min(), h[k:j+1].max(), k, j


def detect(o, h, l, c, atr, n=3, max_gap=60, disp_ratio=0.5, wick_frac=0.6,
           require_through=True, strict_sweep=True, pd_lookback=60):
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n)
    rng_hi = np.full(N, np.nan); rng_lo = np.full(N, np.nan)
    for i in range(pd_lookback, N):
        rng_hi[i] = h[i-pd_lookback:i].max(); rng_lo[i] = l[i-pd_lookback:i].min()

    out = []
    sh = sl = np.nan
    s_lo_i = s_hi_i = -1; s_lo_px = s_hi_px = np.nan; sh_ref = sl_ref = np.nan

    for i in range(n + 3, N):
        if hi[i]: sh = hp[i]
        if lo[i]: sl = lp[i]

        # R3 timeout - the bug that killed v2
        if s_lo_i >= 0 and i - s_lo_i > max_gap: s_lo_i, s_lo_px = -1, np.nan
        if s_hi_i >= 0 and i - s_hi_i > max_gap: s_hi_i, s_hi_px = -1, np.nan

        rng_i = max(h[i] - l[i], 1e-12)
        # CORRECTION 1 - wick through, close back, 60% rejection
        if not np.isnan(sl) and l[i] < sl:
            ok = (c[i] > sl and (c[i] - l[i]) > wick_frac * rng_i) if strict_sweep else True
            if ok and (s_lo_i < 0 or l[i] < s_lo_px):
                s_lo_i, s_lo_px, sh_ref = i, l[i], sh
        if not np.isnan(sh) and h[i] > sh:
            ok = (c[i] < sh and (h[i] - c[i]) > wick_frac * rng_i) if strict_sweep else True
            if ok and (s_hi_i < 0 or h[i] > s_hi_px):
                s_hi_i, s_hi_px, sl_ref = i, h[i], sl

        if np.isnan(atr[i]) or atr[i] <= 0: continue
        body = abs(c[i] - o[i])
        if body / rng_i < disp_ratio: continue

        for side in (1, -1):
            if side == 1:
                sw_i, sw_px, ref = s_lo_i, s_lo_px, sh_ref
                mss = (not np.isnan(ref)) and c[i] > ref and c[i] > o[i]
            else:
                sw_i, sw_px, ref = s_hi_i, s_hi_px, sl_ref
                mss = (not np.isnan(ref)) and c[i] < ref and c[i] < o[i]
            if not (sw_i > 0 and 0 < i - sw_i <= max_gap and mss): continue

            bz = _block(o, c, h, l, sw_i, i, side == 1)
            if bz is None: continue
            b_lo, b_hi, b_wlo, b_whi, k0, k1 = bz
            # CORRECTION 3 - displacement must trade through the block's far extreme
            if require_through and ((side == 1 and h[i] < b_whi) or (side == -1 and l[i] > b_wlo)):
                continue

            found = None
            for k in range(sw_i + 2, i + 1):
                if side == 1 and l[k] > h[k-2]:
                    z = (max(h[k-2], b_lo), min(l[k], b_hi))
                elif side == -1 and h[k] < l[k-2]:
                    z = (max(h[k], b_lo), min(l[k-2], b_hi))
                else: continue
                if z[1] > z[0]: found = z; break
            if found:
                out.append(dict(bar=i, side=side, zone_lo=found[0], zone_hi=found[1],
                                sweep_px=sw_px, sweep_bar=sw_i,
                                brk_lo=b_lo, brk_hi=b_hi,           # bodies
                                mt=(b_lo + b_hi) / 2,               # mean threshold
                                mss_origin=(l[k1] if side == 1 else h[k1]),
                                leg_lo=min(l[sw_i:i+1].min(), sw_px), leg_hi=h[sw_i:i+1].max(),
                                rng_lo=rng_lo[i], rng_hi=rng_hi[i],
                                d_body_ratio=body / rng_i,
                                d_opp_wick=((h[i]-max(o[i],c[i])) if side==1 else (min(o[i],c[i])-l[i]))/rng_i,
                                d_body_avg=body / max(np.nanmean(np.abs(c[max(0,i-20):i]-o[max(0,i-20):i])), 1e-12),
                                d_fvg_w=(found[1]-found[0]) / atr[i],
                                sh_hist=[], sl_hist=[]))
            if side == 1: s_lo_i = -1
            else: s_hi_i = -1
    return out
