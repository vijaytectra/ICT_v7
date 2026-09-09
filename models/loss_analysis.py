"""Why do the losing trades lose — and is any of it avoidable BEFORE entry?

The dangerous version of this question conditions on the outcome: look at the losses,
add a rule that removes them.  That is curve fitting by construction, and this project
has already produced the textbook example (LR4 partial takes: win rate 47.9% -> 58.5%,
expectancy +0.295R -> +0.097R).

The legitimate version, and the one run here:

  1  attach only CAUSAL features - everything knowable at or before the fill;
  2  split the whole population by each feature, not just the losses;
  3  ask which cohorts have NEGATIVE expectancy, since only those are worth removing;
  4  require a mechanism, not just a number;
  5  validate on the 2015-2023 holdout, nine years the model has never seen.

Nothing here changes the locked config.  `extra=` in ict_bt.run defaults to None.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_bt, ict_system

f = lambda x: f"{x:.3f}"
EXTRA = ["ah", "al", "pdh", "pdl", "bias", "stl", "sweep_px", "ce",
         "zone_lo", "zone_hi"]

_P = {}


def prep(sym, path=None):
    if sym not in _P:
        df = pd.read_parquet(L.DATA / f"{path or sym}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        _P[sym] = (df, bars, atr, sigs)
    return _P[sym]


def featured(sym, unit, cost, path=None):
    """The locked trades, plus causal pre-entry features."""
    df, bars, atr, sigs = prep(sym, path)
    kw = dict(L.EXECUTE); kw["cost"] = cost; kw["extra"] = EXTRA
    t = ict_bt.run(df, sigs, bars.index, unit, pd.Timedelta(L.TF), **kw)
    if not len(t):
        return t
    b = t._bar.values
    h, l, c = bars.h_b.values, bars.l_b.values, bars.c_b.values
    o = bars.o_b.values
    med_atr = np.nanmedian(atr[np.isfinite(atr)])

    t["sym"] = sym
    t["asia_w"] = (t.ah - t.al) / unit                       # session range, units
    t["asia_w_atr"] = (t.ah - t.al) / atr[b]                 # ... relative to volatility
    # how far past the bound the raid went, as a fraction of the range
    depth = np.where(t.side == 1, t.al - t.sweep_px, t.sweep_px - t.ah)
    t["depth"] = depth / np.maximum(t.ah - t.al, 1e-12)
    t["lag"] = t._bar - t._sweep_bar                         # M15 bars raid -> signal
    t["fvg_atr"] = (t.zone_hi - t.zone_lo) / atr[b]
    t["disp"] = np.abs(c[b] - o[b]) / np.maximum(h[b] - l[b], 1e-12)
    t["atr_pct"] = atr[b] / med_atr                          # volatility regime
    # where the entry sits inside the Asian range: 0 = at the raided bound, 1 = far side
    pos = np.where(t.side == 1, (t._px - t.al), (t.ah - t._px))
    t["entry_pos"] = pos / np.maximum(t.ah - t.al, 1e-12)
    t["hour"] = t.t.dt.hour                                  # EET
    t["dow"] = t.t.dt.dayofweek
    t["has_stl"] = np.isfinite(t.stl.values.astype(float)).astype(int)
    t["bias_agree"] = (np.sign(t.bias) == t.side).astype(int)
    t["fill_lag"] = t._fill_i - 0                            # placeholder, unused
    return t


def live():
    out = [featured(s, L.UNIT[s], L.COST[s]) for s in L.ALL]
    return pd.concat([x for x in out if len(x)]).sort_values("t").reset_index(drop=True)


def hold():
    out = []
    for s, p in (("USATECH", "USATECH_H"), ("USA500", "USA500_H"),
                 ("USA30", "USA30_H")):
        out.append(featured(s + "_H", 1.0, 1.5, p))
    return pd.concat([x for x in out if len(x)]).sort_values("t").reset_index(drop=True)


def cohort(t, col, bins=None, q=4, label=None):
    d = t.copy()
    if bins is not None:
        d["_c"] = pd.cut(d[col], bins)
    elif d[col].nunique() <= 12:
        d["_c"] = d[col]
    else:
        d["_c"] = pd.qcut(d[col], q, duplicates="drop")
    rows = []
    for k, g in d.groupby("_c", observed=True):
        v = g.netR.values
        gl = -v[v < 0].sum()
        rows.append(dict(feature=label or col, cohort=str(k), n=len(g),
                         WR=float((g.out == 1).mean()), ER=float(v.mean()),
                         PF=float(v[v > 0].sum() / gl) if gl else np.inf,
                         totR=float(v.sum())))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    t = live()
    print("=" * 96)
    print("WHERE THE 333 LOSSES ACTUALLY SIT")
    print("=" * 96)
    lo = t[t.out == -1]
    print(f"\n  {len(lo)} losses of {len(t)} trades, {lo.netR.sum():+.1f}R\n")
    print("  by side:")
    for s, g in t.groupby("side"):
        gl = g[g.out == -1]
        print(f"    {'LONG ' if s==1 else 'SHORT'}  {len(gl):3d} losses / {len(g):3d} "
              f"trades ({len(gl)/len(g)*100:4.1f}%)   net {g.netR.sum():+7.1f}R   "
              f"PF {L.pf(g.netR.values):.3f}")
    print("\n  by instrument (net R, worst first):")
    bysym = t.groupby("sym").agg(n=("netR", "size"), net=("netR", "sum"),
                                 PF=("netR", lambda v: L.pf(v.values))).sort_values("net")
    print(bysym.to_string(float_format=f))

    print("\n" + "=" * 96)
    print("CAUSAL FEATURE SCAN — every cohort, not just the losing ones")
    print("=" * 96)
    scans = [
        ("R_pips", None, 5, "stop size (units)"),
        ("rr", [2, 2.5, 3, 4, 5, 7, 10], None, "planned R:R"),
        ("asia_w_atr", None, 4, "Asian range / ATR"),
        ("depth", None, 4, "raid depth past the bound"),
        ("lag", [0, 2, 5, 10, 20, 40], None, "M15 bars raid->signal"),
        ("fvg_atr", None, 4, "FVG size / ATR"),
        ("disp", [0.5, 0.6, 0.7, 0.8, 1.0], None, "displacement body ratio"),
        ("atr_pct", None, 4, "volatility regime"),
        ("entry_pos", None, 4, "entry depth inside the range"),
        ("hour", None, None, "fill hour EET"),
        ("dow", None, None, "day of week"),
        ("bias_agree", None, None, "daily bias agrees"),
        ("has_stl", None, None, "short-term low present"),
    ]
    allc = []
    for col, bins, q, lab in scans:
        c = cohort(t, col, bins, q or 4, lab)
        allc.append(c)
        print("\n" + c.to_string(index=False, float_format=f))
    C = pd.concat(allc)
    C.to_csv(r"C:\personal\ICT_v7\reports\loss_cohorts.csv", index=False)

    print("\n" + "=" * 96)
    print("CANDIDATES — cohorts with NEGATIVE expectancy and n >= 25")
    print("=" * 96)
    bad = C[(C.ER < 0) & (C.n >= 25)].sort_values("ER")
    print(bad.to_string(index=False, float_format=f) if len(bad) else "  none")
