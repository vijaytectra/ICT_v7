"""Pre-live protocol on the LOCKED Asian-range model.

Tests 1, 2, 3, 7 from the review list - the ones never run on this model.
Nothing is optimised here.  The rules are frozen; only the analysis is new.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models import asia_v3, ict_bt, ict_system

pd.set_option("display.width", 210); f = lambda x: f"{x:.3f}"
IDX = ["USATECH", "USA500", "USA30"]
_C = {}


def data(sym, hold):
    k = (sym, hold)
    if k not in _C:
        p = sym + "_H" if hold else sym
        df = pd.read_parquet(L.DATA / f"{p}.parquet"); bars, atr = L.resample(df)
        _C[k] = (df, bars, atr, ict_system.daily_context(df), ict_system.session_pools(df))
    return _C[k]


def book(syms, hold, shorts=False):
    """The locked rules, exactly.  Arm A = mss; Arm B = reclaim + London raid."""
    det = dict(L.DETECT_B) if shorts else dict(L.DETECT)
    out = []
    for s in syms:
        df, bars, atr, ctx, asia = data(s, hold)
        sigs = (asia_v3.detect(df, bars, atr, ctx, asia, **det) if shorts
                else ict_system.detect(df, bars, atr, ctx, asia, **det))
        kw = dict(L.EXECUTE); kw["cost"] = 1.5 if hold else L.COST[s]
        t = ict_bt.run(df, sigs, bars.index, 1.0 if hold else L.UNIT[s],
                       pd.Timedelta(L.TF), **kw)
        if len(t):
            t = t[~t.t.dt.dayofweek.isin([0])]
            if shorts and len(t): t = t[t.side == -1]
            if len(t): t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def dd(v):
    eq = np.cumsum(v)
    return float((eq - np.maximum.accumulate(eq)).min())


def streak(v):
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    return mx


# ------------------------------------------------------------------- TEST 1
def monte_carlo(v, iters=20000, seed=17):
    """Reshuffle the actual R sequence.  Same edge, different path."""
    r = np.random.default_rng(seed)
    n = len(v)
    dds, ends, stks = np.empty(iters), np.empty(iters), np.empty(iters)
    for i in range(iters):
        p = r.permutation(v)
        eq = np.cumsum(p)
        dds[i] = (eq - np.maximum.accumulate(eq)).min()
        ends[i] = eq[-1]
        stks[i] = streak(p)
    return dds, ends, stks


if __name__ == "__main__":
    books = {"ARM A live 2024-26": book(L.ALL, False, False),
             "ARM B live 2024-26": book(L.ALL, False, True),
             "ARM A hold 2015-23": book(IDX, True, False),
             "ARM B hold 2015-23": book(IDX, True, True)}
    for k, v in books.items():
        v.to_csv(rf"C:\personal\ICT_v7\reports\proto_{k.split()[1]}_{k.split()[2]}.csv",
                 index=False)

    print("=" * 112)
    print("EXACT TRADE ECONOMICS  (the review asked for these explicitly)")
    print("=" * 112)
    rows = []
    for k, d in books.items():
        w = d[d.out == 1].netR; ls = d[d.out == -1].netR
        rows.append(dict(book=k, n=len(d), WR=float((d.out == 1).mean()),
                         avg_win=w.mean(), avg_loss=ls.mean(),
                         win_loss_ratio=abs(w.mean() / ls.mean()),
                         expectancy=d.netR.mean(), median_R=d.netR.median(),
                         PF=L.pf(d.netR.values), totR=d.netR.sum()))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n" + "=" * 112)
    print("TEST 1 — MONTE CARLO, 20,000 reshuffles of the actual R sequence")
    print("=" * 112)
    rows = []
    for k, d in books.items():
        v = d.netR.values
        dds, ends, stks = monte_carlo(v)
        rows.append(dict(book=k, actual_DD=dd(v), median_DD=np.median(dds),
                         DD_p95=np.percentile(dds, 5), DD_worst=dds.min(),
                         actual_streak=streak(v), streak_p95=np.percentile(stks, 95),
                         streak_worst=int(stks.max()),
                         P_end_negative=float((ends < 0).mean()),
                         P_DD_worse_2x=float((dds < 2 * dd(v)).mean()),
                         P_end_gt_half=float((ends > 0.5 * v.sum()).mean())))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))
    print("\n  actual_DD is what happened; DD_p95 is the 5th percentile (a bad but not")
    print("  extreme path); DD_worst is the worst of 20,000 reshuffles.")


# ------------------------------------------------------------- TESTS 2 and 3
def per_period(d, freq):
    g = d.set_index("t").netR.groupby(pd.Grouper(freq=freq))
    r = g.agg(["size", "sum"])
    r["PF"] = g.apply(lambda v: L.pf(v.values) if len(v) else np.nan)
    r["WR"] = d.set_index("t").out.groupby(pd.Grouper(freq=freq)).apply(
        lambda v: (v == 1).mean() if len(v) else np.nan)
    return r[r["size"] > 0]


def loyo(d, label):
    """Leave-one-year-out: what does the record look like without each year?"""
    d = d.copy(); d["y"] = d.t.dt.year
    rows = []
    tot = d.netR.sum(); pf_all = L.pf(d.netR.values)
    for y in sorted(d.y.unique()):
        sub = d[d.y == y]; rest = d[d.y != y]
        rows.append(dict(book=label, year=y, n=len(sub), PF_year=L.pf(sub.netR.values),
                         totR_year=sub.netR.sum(),
                         n_wo=len(rest), PF_without=L.pf(rest.netR.values),
                         totR_without=rest.netR.sum(),
                         share_of_total=sub.netR.sum() / tot if tot else np.nan))
    return pd.DataFrame(rows), pf_all


def walk_forward(d, label, months=6):
    """Rolling windows, frozen rules.  Nothing is re-optimised, so every window is
    genuinely out-of-sample for a trader who fixed the rules before it began."""
    r = per_period(d, f"{months}MS")
    r = r.rename(columns={"size": "n", "sum": "totR"})
    r["book"] = label
    return r
