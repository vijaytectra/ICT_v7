"""MMXM v4 — four implementation errors corrected against the source material.

v2/v3 measured MMXM at PF 1.168 (all 9, real cost).  Re-reading the corpus against the
code found four places where the implementation does not do what the doctrine says.
None of them is a parameter choice; each is a rule that was simply not implemented.

  1  THE TARGET WAS NEVER CHECKED FOR BEING UNSWEPT.
     `02-liquidity/draw-on-liquidity.md`, Formal Criteria: "A DOL must be: an
     identifiable, UNSWEPT liquidity-pool ... not_yet_swept(pool) == true".
     v2 targeted the opposite accumulation bound unconditionally.  If price had
     already taken that bound earlier in the session, the trade was aimed at liquidity
     that no longer exists.

  2  THERE WAS NO R:R GATE.
     `targets-and-exits.md`: "if rr_planned < min_rr the setup is skipped even if every
     other box is checked."  v2 ran min_rr=1.0 and no maximum.  On the Asian-range model
     this gate is the single largest measured lever in the whole project (+0.18 PF), and
     the cohort it rejects was separately shown to lose money at every target from 1R to
     4R across both periods (n~900).

  3  THE POOL SET WAS TOO NARROW.
     `02-liquidity/liquidity-pool.md`: pools are swing highs/lows, equal highs/lows,
     session extremes, AND the prior day / prior week extremes.  v2 only ever looked at
     the opposite accumulation bound.

  4  THE ENTRY IGNORED THE 2025 CE REFINEMENT.
     `06-fair-value-gaps/ce-as-primary-entry.md`: "the default entry inside an FVG is
     CE (50% midpoint) ... deviate only with a reason."  v2 entered at the order block's
     mean threshold and did not use the displacement FVG at all.

Phases A-C are unchanged from mmxm2 (accumulation range, manipulation sweep of its
bound, CISD reversal).  Only the target and entry are rebuilt.
"""
import numpy as np
import pandas as pd

from models.mmxm2 import A_WIN, accumulation, swings


def pool_clock(bars, acc, a_win=A_WIN):
    """Per bar, which pools have ALREADY been taken today.

    A pool that has been swept is no longer a draw (draw-on-liquidity.md).  Tracks the
    accumulation-range bounds and the previous day's high/low, from the moment the
    accumulation window closes.
    """
    idx = bars.index
    day = idx.normalize()
    hour = idx.hour
    lo, hi = bars.l_b.values, bars.h_b.values
    A = acc.reindex(day)
    al, ah = A.acc_lo.values, A.acc_hi.values
    pdl, pdh = A.pdl.values, A.pdh.values
    N = len(idx)
    out = np.zeros((N, 4), bool)          # acc_lo, acc_hi, pdl, pdh
    cur = None
    f = np.zeros(4, bool)
    for i in range(N):
        if day[i] != cur:
            cur = day[i]; f[:] = False
        if hour[i] >= a_win[1]:
            if np.isfinite(al[i]) and lo[i] < al[i]: f[0] = True
            if np.isfinite(ah[i]) and hi[i] > ah[i]: f[1] = True
            if np.isfinite(pdl[i]) and lo[i] < pdl[i]: f[2] = True
            if np.isfinite(pdh[i]) and hi[i] > pdh[i]: f[3] = True
        out[i] = f
    return pd.DataFrame(out, index=idx,
                        columns=["s_acc_lo", "s_acc_hi", "s_pdl", "s_pdh"])


def detect(bars, acc, clock, peers=None, htf_bias=None, n=5, m_win=None,
           require_contraction=False, require_smt=False, require_judas=False,
           require_bias=False, max_leg=10, max_hold_bars=60, disp_ratio=0.0,
           require_fvg=False, ob_zone="body", entry_mode="ce",
           pools=("accum", "pd")):
    """entry_mode: 'ce'  consequent encroachment of the displacement FVG, falling back
                        to the order-block mean threshold when the leg left no gap
                        (ce-as-primary-entry.md)
                   'mt'  order-block mean threshold only (v2 behaviour)
       pools:      which draw candidates to consider, each checked UNSWEPT
    """
    idx = bars.index
    o, h, l, c = bars.o_b.values, bars.h_b.values, bars.l_b.values, bars.c_b.values
    N = len(c)
    day = idx.normalize()
    hour = idx.hour
    A = acc.reindex(day)
    acc_lo, acc_hi = A.acc_lo.values, A.acc_hi.values
    pdl, pdh = A.pdl.values, A.pdh.values
    contr = A.contraction.values.astype(bool)
    K = clock.reindex(idx).values                      # s_acc_lo, s_acc_hi, s_pdl, s_pdh
    bias = (htf_bias.reindex(idx, method="ffill").values
            if htf_bias is not None else np.zeros(N))
    peer_lo = peer_hi = None
    if peers:
        peer_lo = np.column_stack([p.swept_lo.values for p in peers.values()])
        peer_hi = np.column_stack([p.swept_hi.values for p in peers.values()])

    out = []
    st = {1: None, -1: None}
    cur_day = None
    A_END = A_WIN[1]

    for i in range(n + 3, N):
        if day[i] != cur_day:
            cur_day = day[i]; st = {1: None, -1: None}
        if hour[i] < A_END:
            continue
        if not (np.isfinite(acc_lo[i]) and np.isfinite(acc_hi[i])):
            continue
        if require_contraction and not contr[i]:
            continue
        in_judas = (m_win is None) or (m_win[0] <= hour[i] < m_win[1])

        for side in (1, -1):
            bound = acc_lo[i] if side == 1 else acc_hi[i]
            took = (l[i] < bound) if side == 1 else (h[i] > bound)
            if st[side] is None:
                if not took:
                    continue
                if require_judas and not in_judas:
                    continue
                if require_bias and bias[i] != 0 and np.sign(bias[i]) != side:
                    continue
                if require_smt:
                    if peer_lo is None:
                        continue
                    row = peer_lo[i] if side == 1 else peer_hi[i]
                    if row.all():
                        continue
                st[side] = dict(ext=l[i] if side == 1 else h[i], ext_bar=i, start=i)
                continue

            s = st[side]
            if i - s["start"] > max_hold_bars:
                st[side] = None; continue
            if side == 1 and l[i] < s["ext"]: s["ext"], s["ext_bar"] = l[i], i
            if side == -1 and h[i] > s["ext"]: s["ext"], s["ext_bar"] = h[i], i
            if i <= s["ext_bar"]:
                continue

            # ---------------- PHASE C : CISD ------------------------------------
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

            # -------- FIX 4 : entry defaults to the FVG's CE ---------------------
            if entry_mode == "ce" and gap is not None:
                px = (gap[0] + gap[1]) / 2
            else:
                px = (z_lo + z_hi) / 2

            # -------- FIX 1 + 3 : the draw must be an UNSWEPT pool ---------------
            cand = []
            if "accum" in pools:
                v = acc_hi[i] if side == 1 else acc_lo[i]
                swept = K[i][1] if side == 1 else K[i][0]
                if np.isfinite(v) and not swept:
                    cand.append(v)
            if "pd" in pools:
                v = pdh[i] if side == 1 else pdl[i]
                swept = K[i][3] if side == 1 else K[i][2]
                if np.isfinite(v) and not swept:
                    cand.append(v)
            cand = [v for v in cand if (v > px if side == 1 else v < px)]
            if not cand:
                continue
            tgt = min(cand) if side == 1 else max(cand)   # the NEAREST unswept pool

            out.append(dict(
                bar=i, side=side, sweep_px=s["ext"], sweep_bar=s["ext_bar"],
                zone_lo=z_lo, zone_hi=z_hi, mt=(z_lo + z_hi) / 2, ce=px, cisd=ref,
                target=tgt, acc_lo=acc_lo[i], acc_hi=acc_hi[i],
                contraction=bool(contr[i]), leg=len(leg), bias=bias[i],
                d_body=abs(c[i] - o[i]) / rng_i,
                fvg_lo=gap[0] if gap else np.nan,
                fvg_hi=gap[1] if gap else np.nan,
                poi_lo=np.nan, erl_hi=np.nan, erl_lo=np.nan))
            st[side] = None
    return out
