"""ICT Unicorn Model — mechanical spec consolidated from three sources.

  OpenMobius KB  knowledge_base/concepts/unicorn_model.json
  brodenbeck1    models/ict/unicorn/unicorn.md
  SrsBlack       concepts/31-models/unicorn-model.md

Bullish (bearish mirrors):
  1. confirmed swing low SL; the confirmed swing high above it is FROZEN at sweep time
  2. SWEEP: price trades below SL                      (mandatory raid, all 3 sources)
  3. DISPLACEMENT: a later candle CLOSES above the frozen swing high (MSS),
     and the leg from the sweep is >= disp_k * ATR
  4. BREAKER: the last consecutive run of down-close candles before the leg;
     zone = [min low, max high] of that run, wicks included (KB: whole sequence)
  5. FVG: any 3-candle gap left ANYWHERE in the displacement leg
  6. OVERLAP of breaker zone and an FVG must be NON-EMPTY (adjacency does not count)
  7. ENTRY: limit at the overlap edge on the first retrace, within `window` bars
  8. STOP: beyond the sweep extreme                     (structure-based, per operator)

Causality: a swing at index j needs n bars each side, so it is CONFIRMED at j+n and
is invisible to any decision before that bar. Enforced by marking swings at j+n.
"""
import numpy as np


def swings(h, l, n):
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        wh = h[i-n:i+n+1]; wl = l[i-n:i+n+1]
        if wh.argmax() == n: hi[i+n] = True; hp[i+n] = h[i]
        if wl.argmin() == n: lo[i+n] = True; lp[i+n] = l[i]
    return hi, hp, lo, lp


def _breaker(o, c, h, l, start, end, want_down):
    """Last consecutive run of down-(or up-)close candles in [start, end)."""
    j = end - 1
    while j >= start and ((c[j] < o[j]) != want_down):
        j -= 1
    if j < start: return None
    k = j
    while k - 1 >= start and ((c[k-1] < o[k-1]) == want_down):
        k -= 1
    return (l[k:j+1].min(), h[k:j+1].max())


def detect(o, h, l, c, atr, n=3, disp_k=1.0, max_gap=60):
    N = len(c)
    hi, hp, lo, lp = swings(h, l, n)
    sigs = []
    sh = np.nan; sl = np.nan
    sweep_lo_i = -1; sweep_lo_px = np.nan; sh_ref = np.nan
    sweep_hi_i = -1; sweep_hi_px = np.nan; sl_ref = np.nan

    for i in range(n + 3, N):
        if hi[i]: sh = hp[i]
        if lo[i]: sl = lp[i]

        # ---- 2. sweep: freeze the opposing swing at the moment of the raid ----
        if not np.isnan(sl) and l[i] < sl:
            if sweep_lo_i < 0 or l[i] < sweep_lo_px:
                sweep_lo_i, sweep_lo_px, sh_ref = i, l[i], sh
        if not np.isnan(sh) and h[i] > sh:
            if sweep_hi_i < 0 or h[i] > sweep_hi_px:
                sweep_hi_i, sweep_hi_px, sl_ref = i, h[i], sl

        if np.isnan(atr[i]) or atr[i] <= 0: continue

        # ---- BULLISH -------------------------------------------------------
        if (sweep_lo_i > 0 and not np.isnan(sh_ref) and 0 < i - sweep_lo_i <= max_gap
                and c[i] > sh_ref and c[i] > o[i]
                and (c[i] - sweep_lo_px) >= disp_k * atr[i]):          # 3. MSS + leg
            brk = _breaker(o, c, h, l, sweep_lo_i, i, True)            # 4. breaker
            if brk:
                for k in range(sweep_lo_i + 2, i + 1):                 # 5. FVG in leg
                    if l[k] > h[k-2]:
                        ov_lo = max(h[k-2], brk[0]); ov_hi = min(l[k], brk[1])
                        if ov_hi > ov_lo:                              # 6. overlap
                            sigs.append(dict(bar=i, side=1, zone_lo=ov_lo, zone_hi=ov_hi,
                                             stop=sweep_lo_px, sweep_bar=sweep_lo_i))
                            break
                sweep_lo_i = -1

        # ---- BEARISH -------------------------------------------------------
        if (sweep_hi_i > 0 and not np.isnan(sl_ref) and 0 < i - sweep_hi_i <= max_gap
                and c[i] < sl_ref and c[i] < o[i]
                and (sweep_hi_px - c[i]) >= disp_k * atr[i]):
            brk = _breaker(o, c, h, l, sweep_hi_i, i, False)
            if brk:
                for k in range(sweep_hi_i + 2, i + 1):
                    if h[k] < l[k-2]:
                        ov_lo = max(h[k], brk[0]); ov_hi = min(l[k-2], brk[1])
                        if ov_hi > ov_lo:
                            sigs.append(dict(bar=i, side=-1, zone_lo=ov_lo, zone_hi=ov_hi,
                                             stop=sweep_hi_px, sweep_bar=sweep_hi_i))
                            break
                sweep_hi_i = -1
    return sigs
