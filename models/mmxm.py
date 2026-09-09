"""Market Maker Buy / Sell Model (MMXM) + Market Maker Trap.

The four-phase curve, detected prospectively, every value knowable at the bar it is
emitted on.

  A  ACCUMULATION   the POI - an unfilled HTF fair value gap (internal range liquidity)
                    that price is trading into, in discount/premium.   [OpenMobius MMBM
                    identification_rules 1-2; brodenbeck IRL/ERL alternation]
  B  MANIPULATION   inside the POI, a sell-side pool is taken.  The market-maker-trap
                    reading: a break against higher-timeframe order flow IS the
                    accumulation event, and the pool may be measured off candle BODIES
                    rather than wicks.                             [SrsBlack MM-trap c8]
  C  SMR            CISD - a close above the highest high of the consecutive down-close
                    candles that made the manipulation low.  That same candle run is
                    the order block.                               [brodenbeck CISD]
  D  DISTRIBUTION   redelivery from internal back out to external range liquidity.

Bearish mirrors exactly.  Nothing here reads a bar later than the one it stands on;
tests/test_mmxm_invariants.py enforces that with a prefix-invariance test.
"""
import numpy as np
import pandas as pd


# --------------------------------------------------------------------------- swings
def swings(h, l, n):
    """Confirmed swing points, marked at the bar they become knowable (pivot + n)."""
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    hb = np.full(N, -1, int); lb = np.full(N, -1, int)
    for i in range(n, N - n):
        if h[i - n:i + n + 1].argmax() == n:
            hi[i + n] = True; hp[i + n] = h[i]; hb[i + n] = i
        if l[i - n:i + n + 1].argmin() == n:
            lo[i + n] = True; lp[i + n] = l[i]; lb[i + n] = i
    return hi, hp, hb, lo, lp, lb


# ----------------------------------------------------------------------- HTF context
def htf_context(df, htf="4h", n=2, max_fvg_age=60):
    """Dealing range, institutional order flow and the FVG inventory of the HTF.

    ctx is indexed by the time each HTF bar CLOSES - the first moment its content is
    knowable.  fvgs is a list of (available_from, side, lo, hi, expiry_time).
    """
    b = df[["o_b", "h_b", "l_b", "c_b"]].resample(htf).agg(
        {"o_b": "first", "h_b": "max", "l_b": "min", "c_b": "last"}).dropna()
    delta = pd.Timedelta(htf)
    close_t = b.index + delta
    o, h, l, c = b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values
    hi, hp, _, lo, lp, _ = swings(h, l, n)

    N = len(b)
    dr_hi = np.full(N, np.nan); dr_lo = np.full(N, np.nan); bias = np.zeros(N)
    last_hi = last_lo = np.nan
    cur = 0
    for i in range(N):
        if hi[i]: last_hi = hp[i]
        if lo[i]: last_lo = lp[i]
        # institutional order flow = direction of the most recent break of a CONFIRMED
        # swing (brodenbeck top-down-analysis, tier 3)
        if np.isfinite(last_hi) and c[i] > last_hi: cur = 1
        elif np.isfinite(last_lo) and c[i] < last_lo: cur = -1
        dr_hi[i], dr_lo[i], bias[i] = last_hi, last_lo, cur

    ctx = pd.DataFrame({"dr_hi": dr_hi, "dr_lo": dr_lo, "bias": bias}, index=close_t)
    ctx["eqm"] = (ctx.dr_hi + ctx.dr_lo) / 2

    fvgs = []
    for k in range(2, N):
        exp = close_t[min(k + max_fvg_age, N - 1)]
        if l[k] > h[k - 2]:
            fvgs.append((close_t[k], 1, h[k - 2], l[k], exp))      # bullish gap
        if h[k] < l[k - 2]:
            fvgs.append((close_t[k], -1, h[k], l[k - 2], exp))     # bearish gap
    return ctx, fvgs


# ------------------------------------------------------------------------- the model
def detect(bars, ctx, fvgs, n=5, poi_mode="fvg", sweep_pool="swing",
           body_liquidity=False, require_bias=True, require_discount=True,
           max_gap=40, max_leg=10, disp_ratio=0.0, require_fvg=False,
           ob_zone="body", eq_tol_atr=0.25, atr=None):
    """Emit MMXM setups on the structure timeframe.

    poi_mode      'fvg'  price must be inside an unfilled HTF FVG (internal range liq.)
                  'erl'  the HTF dealing-range extreme must have been taken (external)
                  'any'  no POI gate  <- the ablation control for H3
    sweep_pool    'swing' last confirmed structure swing (inducement) | 'asia' the
                  Asian-range extreme, a TIME-DEFINED pool, frozen at 09:00 EET |
                  'equal' relative equal highs/lows | 'none' no pool requirement
    body_liquidity  measure the pool off candle bodies rather than wicks (H4)
    ob_zone       'body' order block = bodies of the manipulation-leg candles;
                  'range' = their full high/low
    """
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    if atr is None:
        tr = pd.concat([bars.h_b - bars.l_b, (bars.h_b - bars.c_b.shift()).abs(),
                        (bars.l_b - bars.c_b.shift()).abs()], axis=1).max(1)
        atr = tr.rolling(14).mean().values
    hi, hp, hb, lo, lp, lb = swings(h, l, n)

    C = ctx.reindex(idx, method="ffill")
    dr_hi, dr_lo, eq, bias = C.dr_hi.values, C.dr_lo.values, C.eqm.values, C.bias.values

    body_lo = np.minimum(o, c); body_hi = np.maximum(o, c)
    pool_lo = np.full(N, np.nan); pool_hi = np.full(N, np.nan)      # 'swing' mode
    eqp_lo = np.full(N, np.nan); eqp_hi = np.full(N, np.nan)        # 'equal' mode
    rl, rh = [], []
    cur_lo = cur_hi = cur_eql = cur_eqh = np.nan
    med_atr = np.nanmedian(atr[np.isfinite(atr)])
    tol = eq_tol_atr * (med_atr if np.isfinite(med_atr) else 0.0)
    for i in range(N):
        if lo[i]:
            v = body_lo[lb[i]] if body_liquidity else lp[i]
            cur_lo = v; rl.append(v)
            if len(rl) >= 2 and abs(rl[-1] - rl[-2]) <= tol:
                cur_eql = min(rl[-1], rl[-2])
        if hi[i]:
            v = body_hi[hb[i]] if body_liquidity else hp[i]
            cur_hi = v; rh.append(v)
            if len(rh) >= 2 and abs(rh[-1] - rh[-2]) <= tol:
                cur_eqh = max(rh[-1], rh[-2])
        pool_lo[i], pool_hi[i] = cur_lo, cur_hi
        eqp_lo[i], eqp_hi[i] = cur_eql, cur_eqh

    # time-defined pool: the Asian range, 02:00-09:00 EET, usable only from 09:00.
    # ict-2022-model.md step 3 names the pools as Asian range / PDH-PDL / session
    # extreme.  A 3-5 bar swing low is inducement, not resting liquidity - measured
    # in this project at PF 1.19 (asia) against 0.76 (PDH/PDL).
    asia_lo = np.full(N, np.nan); asia_hi = np.full(N, np.nan)
    hh, dd = idx.hour, idx.normalize()
    run_lo = run_hi = np.nan
    prev_day = None
    day_lo = day_hi = np.nan
    for i in range(N):
        if dd[i] != prev_day:
            prev_day = dd[i]; run_lo = run_hi = np.nan; day_lo = day_hi = np.nan
        if 2 <= hh[i] < 9:
            run_lo = l[i] if not np.isfinite(run_lo) else min(run_lo, l[i])
            run_hi = h[i] if not np.isfinite(run_hi) else max(run_hi, h[i])
        elif hh[i] >= 9:
            if not np.isfinite(day_lo):
                day_lo, day_hi = run_lo, run_hi      # frozen at the session close
        asia_lo[i], asia_hi[i] = day_lo, day_hi

    fvg_t = [f[0] for f in fvgs]
    fp = 0
    active = []                                # live HTF FVGs: [side, lo, hi, expiry]
    erl_taken = {1: False, -1: False}
    erl_bar = {1: -10 ** 9, -1: -10 ** 9}
    st = {1: None, -1: None}
    out = []

    for i in range(n + 3, N):
        t = idx[i]
        while fp < len(fvg_t) and fvg_t[fp] <= t:
            f = fvgs[fp]; active.append([f[1], f[2], f[3], f[4]]); fp += 1
        # a bullish FVG dies when price CLOSES below it; a bearish one, above it
        active = [a for a in active if a[3] > t
                  and not (a[0] == 1 and c[i] < a[1])
                  and not (a[0] == -1 and c[i] > a[2])]

        # ---- external range liquidity events -----------------------------------
        if np.isfinite(dr_lo[i]) and l[i] < dr_lo[i]:
            erl_taken[1] = True; erl_bar[1] = i
        if np.isfinite(dr_hi[i]) and h[i] > dr_hi[i]:
            erl_taken[-1] = True; erl_bar[-1] = i

        for side in (1, -1):
            # ---------------- PHASE A : arm on the point of interest -------------
            if st[side] is None:
                ok = False
                z = (np.nan, np.nan)
                if poi_mode == "any":
                    ok = True
                elif poi_mode == "erl":
                    ok = erl_taken[side] and i - erl_bar[side] <= max_gap
                else:
                    cand = [a for a in active
                            if a[0] == side and h[i] >= a[1] and l[i] <= a[2]]
                    if cand:
                        a = (max(cand, key=lambda x: x[2]) if side == 1
                             else min(cand, key=lambda x: x[1]))
                        ok = True; z = (a[1], a[2])
                if ok and require_bias and bias[i] != 0 and np.sign(bias[i]) != side:
                    ok = False
                if ok and require_discount and np.isfinite(eq[i]):
                    if side == 1 and c[i] > eq[i]: ok = False
                    if side == -1 and c[i] < eq[i]: ok = False
                if ok:
                    st[side] = dict(poi=i, ext=l[i] if side == 1 else h[i], ext_bar=i,
                                    swept=(sweep_pool == "none"),
                                    poi_lo=z[0], poi_hi=z[1])
                continue

            s = st[side]
            if i - s["poi"] > max_gap:
                st[side] = None; continue

            # ---------------- PHASE B : the manipulation -------------------------
            if side == 1:
                if l[i] < s["ext"]: s["ext"], s["ext_bar"] = l[i], i
                lv = (pool_lo[i] if sweep_pool == "swing" else
                      asia_lo[i] if sweep_pool == "asia" else eqp_lo[i])
                if sweep_pool != "none" and np.isfinite(lv) and l[i] < lv:
                    s["swept"] = True
            else:
                if h[i] > s["ext"]: s["ext"], s["ext_bar"] = h[i], i
                lv = (pool_hi[i] if sweep_pool == "swing" else
                      asia_hi[i] if sweep_pool == "asia" else eqp_hi[i])
                if sweep_pool != "none" and np.isfinite(lv) and h[i] > lv:
                    s["swept"] = True
            if not s["swept"] or i <= s["ext_bar"]:
                continue

            # ---------------- PHASE C : change in state of delivery --------------
            j = s["ext_bar"]
            opp = (lambda k: c[k] < o[k]) if side == 1 else (lambda k: c[k] > o[k])
            if not opp(j): j -= 1
            leg = []
            while j >= 0 and opp(j) and len(leg) < max_leg:
                leg.append(j); j -= 1
            if not leg:
                continue
            ref = max(h[k] for k in leg) if side == 1 else min(l[k] for k in leg)
            if side == 1 and not c[i] > ref: continue
            if side == -1 and not c[i] < ref: continue

            rng_i = max(h[i] - l[i], 1e-12)
            if disp_ratio and abs(c[i] - o[i]) / rng_i < disp_ratio:
                continue

            if ob_zone == "body":
                z_lo = min(min(o[k], c[k]) for k in leg)
                z_hi = max(max(o[k], c[k]) for k in leg)
            else:
                z_lo = min(l[k] for k in leg)
                z_hi = max(h[k] for k in leg)

            gap = None
            for k in range(s["ext_bar"] + 2, i + 1):
                if side == 1 and l[k] > h[k - 2]: gap = (h[k - 2], l[k]); break
                if side == -1 and h[k] < l[k - 2]: gap = (h[k], l[k - 2]); break
            if require_fvg and gap is None:
                continue

            out.append(dict(
                bar=i, side=side, sweep_px=s["ext"], sweep_bar=s["ext_bar"],
                zone_lo=z_lo, zone_hi=z_hi, mt=(z_lo + z_hi) / 2, cisd=ref,
                poi_lo=s["poi_lo"], poi_hi=s["poi_hi"], leg=len(leg),
                erl_hi=dr_hi[i], erl_lo=dr_lo[i], bias=bias[i],
                d_body=abs(c[i] - o[i]) / rng_i,
                fvg_lo=gap[0] if gap else np.nan,
                fvg_hi=gap[1] if gap else np.nan))
            st[side] = None
    return out
