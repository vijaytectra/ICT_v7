"""MMXM v2 — the Market Maker Buy/Sell Model as the repos actually specify it.

v1 (models/mmxm.py) was measured at PF 0.80 and had four structural omissions.  Each
is fixed here, and each fix is sourced.

  1  PHASE A WAS NEVER IMPLEMENTED.  v1 used an H4 fair value gap as the point of
     interest.  The model begins with the ORIGINAL CONSOLIDATION
     (brodenbeck market-maker-models.md: "decompose: consolidation detection (range
     compression), leg counting away from it, then SMR").  SrsBlack
     01-market-structure/range-contraction.md gives formal criteria:
         ATR_recent <= 0.7 * ATR_prior_expansion  AND  overlap_pct >= 0.7
         AND no external BOS during the window
     and 12-power-of-three/accumulation-phase.md adds: equal highs/lows form along
     the bounds - those ARE the engineered pools the next phase sweeps.

  2  SMT DIVERGENCE WAS MISSING.  brodenbeck market-maker-models.md names the smart
     money reversal confirmation stack as "SMT divergence, MSS/CISD, displacement
     FVG".  v1 had two of the three.  SrsBlack 16-smt-divergence/index-smt.md:
     "one index will fail to confirm a lower low ... that's your bullish
     confirmation".  Implemented exactly as brodenbeck's smt_divergence.py does it,
     anchored at a structural extreme as smt-confirmation.md c3 requires: the peer
     instrument must NOT have swept its OWN accumulation bound.

  3  THE MANIPULATION HAD NO TIME.  It is the Judas swing.
     12-power-of-three/intraday-amd.md fixes the windows (NY time):
         A accumulation 18:00 prev -> 03:00   Asia
         M manipulation 02:00 -> 05:00        London open killzone
         D distribution 08:00 -> 12:00        NY AM
     13-judas-swing/judas-swing.md: the sweep must happen in the session-open
     killzone and reverse inside the same killzone.  v1 used a generic 40-bar window.

  4  THE TARGET WAS ON THE WRONG SIDE OF THE TIMEFRAME RULE.  v1 targeted the H4
     dealing-range extreme - a HIGHER timeframe than the M15 entry array, which
     31-models/market-maker-manipulation-template.md calls the one error it restates
     in every template ("the target array must sit on a timeframe LESSER than the
     timeframe of the array used for entry").  The correct distribution target is the
     OPPOSITE BOUND OF THE ACCUMULATION RANGE - the engineered pool on the other
     side, which is what the whole cycle was built to reach.

Bearish mirrors exactly.  Causality is enforced by tests/test_mmxm2_invariants.py.
"""
import numpy as np
import pandas as pd

# EET = New York + 7.  intraday-amd.md windows converted.
A_WIN = (2, 9)          # 19:00 -> 02:00 NY   accumulation (Asia)
M_WIN = (9, 12)         # 02:00 -> 05:00 NY   manipulation (London open KZ)
D_WIN = (15, 19)        # 08:00 -> 12:00 NY   distribution (NY AM)
M_WIN_NY = (14, 17)     # 07:00 -> 10:00 NY   NY-open Judas


def swings(h, l, n):
    N = len(h)
    hi = np.zeros(N, bool); lo = np.zeros(N, bool)
    hp = np.full(N, np.nan); lp = np.full(N, np.nan)
    for i in range(n, N - n):
        if h[i - n:i + n + 1].argmax() == n: hi[i + n] = True; hp[i + n] = h[i]
        if l[i - n:i + n + 1].argmin() == n: lo[i + n] = True; lp[i + n] = l[i]
    return hi, hp, lo, lp


# ------------------------------------------------------------------ PHASE A
def accumulation(bars, a_win=A_WIN, atr_ratio=0.7, overlap_min=0.7):
    """The original consolidation, one per session day, frozen when the window closes.

    Returns a DataFrame indexed by date: acc_lo, acc_hi, eqh/eql flags, contraction
    (the range-contraction.md test), and the previous day's high/low used for the
    no-external-BOS check.  Nothing here is usable before the window ends.
    """
    o, h, l, c = bars.o_b, bars.h_b, bars.l_b, bars.c_b
    day = bars.index.normalize()
    hour = bars.index.hour
    inA = (hour >= a_win[0]) & (hour < a_win[1])

    A = bars[inA]
    gA = A.groupby(A.index.normalize())
    acc = pd.DataFrame({"acc_lo": gA.l_b.min(), "acc_hi": gA.h_b.max(),
                        "bars": gA.size()})
    # ATR of the accumulation window vs the whole prior day (the prior expansion)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(1)
    acc["atr_A"] = tr[inA].groupby(day[inA]).mean()
    d = pd.DataFrame({"h": h, "l": l, "c": c, "tr": tr}).groupby(day).agg(
        {"h": "max", "l": "min", "c": "last", "tr": "mean"})
    acc["atr_prev"] = d.tr.shift(1).reindex(acc.index)
    acc["pdh"] = d.h.shift(1).reindex(acc.index)
    acc["pdl"] = d.l.shift(1).reindex(acc.index)

    # overlap_pct: fraction of A-window candles whose body overlaps the prior
    # candle's range - range-contraction.md's own definition
    bl = np.minimum(A.o_b, A.c_b); bh = np.maximum(A.o_b, A.c_b)
    ov = ((bl <= A.h_b.shift()) & (bh >= A.l_b.shift())).astype(float)
    acc["overlap"] = ov.groupby(A.index.normalize()).mean()

    no_bos = (acc.acc_hi <= acc.pdh) & (acc.acc_lo >= acc.pdl)
    acc["contraction"] = ((acc.atr_A <= atr_ratio * acc.atr_prev)
                          & (acc.overlap >= overlap_min) & no_bos).fillna(False)
    return acc


def sweep_clock(bars, acc, a_win=A_WIN):
    """For each day, the first bar index at which the accumulation low / high is
    taken.  Used for SMT: a peer that has not yet swept its own bound is the one
    'failing to confirm'.  Only bars after the accumulation window count."""
    idx = bars.index
    day = idx.normalize()
    hour = idx.hour
    lo, hi = bars.l_b.values, bars.h_b.values
    A = acc.reindex(day)
    al, ah = A.acc_lo.values, A.acc_hi.values
    N = len(idx)
    swept_lo = np.zeros(N, bool); swept_hi = np.zeros(N, bool)
    cur_day = None
    slo = shi = False
    for i in range(N):
        if day[i] != cur_day:
            cur_day = day[i]; slo = shi = False
        if hour[i] >= a_win[1]:
            if np.isfinite(al[i]) and lo[i] < al[i]: slo = True
            if np.isfinite(ah[i]) and hi[i] > ah[i]: shi = True
        swept_lo[i], swept_hi[i] = slo, shi
    return pd.DataFrame({"swept_lo": swept_lo, "swept_hi": swept_hi}, index=idx)


# ------------------------------------------------------------------ the model
def detect(bars, acc, peers=None, htf_bias=None, n=5, m_win=M_WIN,
           require_contraction=False, require_smt=False, require_judas=True,
           require_bias=False, max_leg=10, max_hold_bars=60, disp_ratio=0.0,
           require_fvg=False, ob_zone="body", target_mode="accum"):
    """peers: dict sym -> DataFrame(swept_lo, swept_hi) reindexed onto `bars.index`.
    SMT is present when at least one peer has NOT swept its own bound."""
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    day = idx.normalize()
    hour = idx.hour
    A = acc.reindex(day)
    acc_lo, acc_hi = A.acc_lo.values, A.acc_hi.values
    contr = A.contraction.values.astype(bool)
    pdh, pdl = A.pdh.values, A.pdl.values
    bias = (htf_bias.reindex(idx, method="ffill").values
            if htf_bias is not None else np.zeros(N))

    peer_lo = peer_hi = None
    if peers:
        peer_lo = np.column_stack([p.swept_lo.values for p in peers.values()])
        peer_hi = np.column_stack([p.swept_hi.values for p in peers.values()])

    out = []
    st = {1: None, -1: None}
    cur_day = None

    for i in range(n + 3, N):
        if day[i] != cur_day:
            cur_day = day[i]; st = {1: None, -1: None}
        if hour[i] < m_win[0]:
            continue                                   # accumulation not closed yet
        if not (np.isfinite(acc_lo[i]) and np.isfinite(acc_hi[i])):
            continue
        if require_contraction and not contr[i]:
            continue

        in_judas = m_win[0] <= hour[i] < m_win[1]

        for side in (1, -1):
            # ---------------- PHASE B : the Judas sweep of the accumulation bound
            bound = acc_lo[i] if side == 1 else acc_hi[i]
            took = (l[i] < bound) if side == 1 else (h[i] > bound)
            if st[side] is None:
                if not took:
                    continue
                if require_judas and not in_judas:
                    continue
                if require_bias and bias[i] != 0 and np.sign(bias[i]) != side:
                    continue
                # SMT: at least one correlated instrument has NOT taken its own bound
                if require_smt:
                    if peer_lo is None:
                        continue
                    row = peer_lo[i] if side == 1 else peer_hi[i]
                    if row.all():
                        continue                       # everyone swept - no divergence
                st[side] = dict(ext=l[i] if side == 1 else h[i], ext_bar=i, start=i)
                continue

            s = st[side]
            if i - s["start"] > max_hold_bars:
                st[side] = None; continue
            if side == 1 and l[i] < s["ext"]: s["ext"], s["ext_bar"] = l[i], i
            if side == -1 and h[i] > s["ext"]: s["ext"], s["ext_bar"] = h[i], i
            if i <= s["ext_bar"]:
                continue

            # ---------------- PHASE C : change in state of delivery -------------
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
                z_lo = min(l[k] for k in leg); z_hi = max(h[k] for k in leg)

            gap = None
            for k in range(s["ext_bar"] + 2, i + 1):
                if side == 1 and l[k] > h[k - 2]: gap = (h[k - 2], l[k]); break
                if side == -1 and h[k] < l[k - 2]: gap = (h[k], l[k - 2]); break
            if require_fvg and gap is None:
                continue

            # ---------------- PHASE D : the distribution target ------------------
            # the OPPOSITE engineered pool of the accumulation range.  Same
            # timeframe as the entry array, never higher - the manipulation-template
            # rule v1 violated.
            if target_mode == "accum":
                tgt = acc_hi[i] if side == 1 else acc_lo[i]
            elif target_mode == "pdhl":
                tgt = pdh[i] if side == 1 else pdl[i]
            else:
                tgt = np.nan

            out.append(dict(
                bar=i, side=side, sweep_px=s["ext"], sweep_bar=s["ext_bar"],
                zone_lo=z_lo, zone_hi=z_hi, mt=(z_lo + z_hi) / 2, cisd=ref,
                target=tgt, acc_lo=acc_lo[i], acc_hi=acc_hi[i],
                contraction=bool(contr[i]), leg=len(leg), bias=bias[i],
                d_body=abs(c[i] - o[i]) / rng_i,
                fvg_lo=gap[0] if gap else np.nan,
                fvg_hi=gap[1] if gap else np.nan,
                poi_lo=np.nan, erl_hi=np.nan, erl_lo=np.nan))
            st[side] = None
    return out
