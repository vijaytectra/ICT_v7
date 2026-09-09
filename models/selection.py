"""Two mechanism-first selection hypotheses, declared before measurement.

The forensic pass closed off stop placement, breakeven, partials, trailing, time stops,
close-based stops, the one-position rule, and all four funnel cohorts.  What remains is
the 33% of losses that never reach +0.25R - a SELECTION problem.

A 13-feature blind scan already ran: 14 candidate filters, 10 failed the holdout, one
survived with a mechanism (skip Monday).  More blind scanning buys mostly false
positives, so what follows is restricted to two hypotheses that the source material
names as decisive, neither of which has ever been applied to this model.

  H1  SMT DIVERGENCE AT THE RAID.
      SrsBlack 16-smt-divergence/smt-confirmation.md calls SMT "the single
      highest-quality confluence factor" and requires "both assets at meaningful
      structural extremes (not random points)".  Here the structural extreme is exactly
      defined: the Asian range bound.  So SMT is present when, at the moment we raid our
      own Asian low, at least one correlated instrument has NOT yet raided its own.
      index-smt.md: "one index will fail to confirm a lower low ... that's your bullish
      confirmation."
      Correlation groups (16-smt-divergence/correlated-pairs-smt.md requires positive
      correlation): {US100, US500, US30}, {EURUSD, GBPUSD, AUDUSD},
      {USDCHF, USDCAD, USDJPY}.

  H2  OBSTRUCTION.
      05-pd-arrays/pd-array-hierarchy.md and 02-liquidity/liquidity-matrix.md: price is
      delivered array to array.  If an unmitigated OPPOSING higher-timeframe fair value
      gap sits between the entry and the draw on liquidity, the move has to be delivered
      through a level that is itself a counter-order zone.  Hypothesis: those setups
      fail more often.

Both are measured on 2024-2026 AND on the 2015-2023 holdout.  Neither is kept unless it
improves both.  The locked model is not modified.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_bt, ict_system, mmxm, mmxm2

GROUPS = {"idx": ["USATECH", "USA500", "USA30"],
          "usd_base": ["EURUSD", "GBPUSD", "AUDUSD"],
          "usd_quote": ["USDCHF", "USDCAD", "USDJPY"]}
GROUP_OF = {s: g for g, m in GROUPS.items() for s in m}

_P = {}


def prep(sym, path=None):
    if sym not in _P:
        p = path or sym
        df = pd.read_parquet(L.DATA / f"{p}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        acc = mmxm2.accumulation(bars, mmxm2.A_WIN)
        clock = mmxm2.sweep_clock(bars, acc, mmxm2.A_WIN)
        ctx, fvgs = mmxm.htf_context(df, "4h", 2, 60)
        _P[sym] = (df, bars, atr, sigs, clock, fvgs)
    return _P[sym]


def annotate(sym, peers, hold=False):
    """Attach smt and obstruction flags to every trade of the locked model."""
    p = sym + "_H" if hold else sym
    df, bars, atr, sigs, clock, fvgs = prep(p, p)
    kw = dict(L.EXECUTE)
    kw["cost"] = 1.5 if hold else L.COST[sym]
    kw["extra"] = ["ah", "al", "pdh", "pdl", "sweep_px", "ce"]
    t = ict_bt.run(df, sigs, bars.index, 1.0 if hold else L.UNIT[sym],
                   pd.Timedelta(L.TF), **kw)
    if not len(t):
        return t
    t = t[~t.t.dt.dayofweek.isin([0])].reset_index(drop=True)
    if not len(t):
        return t

    # ---- H1 : SMT at the raid ------------------------------------------------
    smt = np.zeros(len(t), int)
    if peers:
        pc = {}
        for q in peers:
            qp = q + "_H" if hold else q
            _, qb, _, _, qclock, _ = prep(qp, qp)
            pc[q] = qclock.reindex(bars.index, method="ffill")
        for i, r in t.iterrows():
            b = int(r._sweep_bar)
            col = "swept_lo" if r.side == 1 else "swept_hi"
            vals = [bool(pc[q][col].values[b]) for q in pc]
            smt[i] = int(not all(vals)) if vals else 0
    t["smt"] = smt

    # ---- H2 : an unmitigated opposing HTF FVG between entry and target -------
    obs = np.zeros(len(t), int)
    ft = np.array([f[0] for f in fvgs])
    side_a = np.array([f[1] for f in fvgs])
    lo_a = np.array([f[2] for f in fvgs])
    hi_a = np.array([f[3] for f in fvgs])
    for i, r in t.iterrows():
        px = r._px if "_px" in t.columns else r.ce
        tgt = (min([v for v in (r.pdh, r.ah)
                    if np.isfinite(v) and v > px], default=np.nan) if r.side == 1
               else max([v for v in (r.pdl, r.al)
                         if np.isfinite(v) and v < px], default=np.nan))
        if not np.isfinite(tgt):
            continue
        live = (ft <= r.t) & (side_a == -r.side)
        lo_b, hi_b = (px, tgt) if r.side == 1 else (tgt, px)
        obs[i] = int(np.any(live & (hi_a >= lo_b) & (lo_a <= hi_b)))
    t["obstruct"] = obs
    t["sym"] = sym
    return t


def build(hold=False):
    syms = ["USATECH", "USA500", "USA30"] if hold else L.ALL
    out = []
    for s in syms:
        peers = [q for q in GROUPS[GROUP_OF[s]] if q != s]
        if hold:
            peers = [q for q in peers if q in ("USATECH", "USA500", "USA30")]
        t = annotate(s, peers, hold)
        if len(t):
            out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True)


def cut(t, col, label):
    rows = []
    for v, g in t.groupby(col):
        x = g.netR.values
        gl = -x[x < 0].sum()
        p, ci = L.bootstrap(x)
        rows.append(dict(rule=f"{label}={v}", n=len(g), WR=float((g.out == 1).mean()),
                         ER=float(x.mean()),
                         PF=float(x[x > 0].sum() / gl) if gl else np.inf,
                         totR=float(x.sum()), P_edge=p))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    f = lambda x: f"{x:.3f}"
    pd.set_option("display.width", 200)
    lv, hd = build(False), build(True)
    lv.to_csv(r"C:\personal\ICT_v7\reports\selection_live.csv", index=False)
    hd.to_csv(r"C:\personal\ICT_v7\reports\selection_hold.csv", index=False)
    for nm, d in (("2024-2026 (9 instruments)", lv),
                  ("2015-2023 holdout (3 indices)", hd)):
        x = d.netR.values
        print("=" * 96)
        print(f"{nm}   base n={len(d)} PF={L.pf(x):.3f} totR={x.sum():+.1f}")
        print("=" * 96)
        print("\nH1  SMT divergence present at the raid")
        print(cut(d, "smt", "smt").to_string(index=False, float_format=f))
        print("\nH2  unmitigated opposing H4 FVG between entry and target")
        print(cut(d, "obstruct", "obstruct").to_string(index=False, float_format=f))
        both = d[(d.smt == 1) & (d.obstruct == 0)]
        if len(both) > 20:
            y = both.netR.values
            gl = -y[y < 0].sum()
            print(f"\n  SMT=1 AND obstruct=0 : n={len(both)}  "
                  f"PF={y[y>0].sum()/gl:.3f}  totR={y.sum():+.1f}")
        print()
