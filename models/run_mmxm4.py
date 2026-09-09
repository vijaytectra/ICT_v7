"""MMXM v4 — the four corrected rules, measured against v2 on both periods."""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as AL
from models import mmxm, mmxm2, mmxm4, mmxm_bt

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"
IDX = ["USATECH", "USA500", "USA30"]
FX = [s for s in AL.ALL if s not in IDX]
COST = {**{s: 1.5 for s in IDX}, **{s: 0.8 for s in FX}}
DET = dict(n=5, max_hold_bars=60, require_smt=False, require_contraction=False,
           require_judas=False, require_bias=False)
_C = {}


def prep(sym, hold=False):
    k = (sym, hold)
    if k not in _C:
        p = sym + "_H" if hold else sym
        df = pd.read_parquet(AL.DATA / f"{p}.parquet")
        bars, atr = AL.resample(df)
        acc = mmxm2.accumulation(bars, mmxm2.A_WIN)
        clock = mmxm4.pool_clock(bars, acc, mmxm2.A_WIN)
        ctx, _ = mmxm.htf_context(df, "1D", 2)
        _C[k] = (df, bars, acc, clock, ctx.bias)
    return _C[k]


def book(syms, hold=False, period=None, mult=1.0, shorts=True, skip_mon=True,
         min_rr=2.0, max_rr=10.0, **det):
    out = []
    for s in syms:
        df, bars, acc, clock, bias = prep(s, hold)
        sigs = mmxm4.detect(bars, acc, clock, htf_bias=bias, **{**DET, **det})
        e = dict(entry="ce", kz="ALL", target="pool", min_rr=min_rr,
                 cost=(1.5 if hold else COST[s]) * mult)
        if e["cost"] > 0:
            e["max_cost_frac"] = 0.20
        t = mmxm_bt.run(df, sigs, bars.index, 1.0 if hold else AL.UNIT[s],
                        pd.Timedelta("15min"), **e)
        if not len(t):
            continue
        if max_rr:
            t = t[t.rr <= max_rr]
        if skip_mon:
            t = t[t.t.dt.dayofweek != 0]
        if shorts:
            t = t[t.side == -1]
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    d = pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()
    if len(d) and period:
        d = d[d.t < AL.IS_END] if period == "IS" else d[d.t >= AL.IS_END]
    return d


def st(d, l):
    if d is None or len(d) < 25:
        return dict(arm=l, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = mmxm_bt.bootstrap(d)
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    return dict(arm=l, n=len(v), WR=float((v > 0).mean()), ER=v.mean(), PF=AL.pf(v),
                totR=v.sum(), maxDD=(eq - np.maximum.accumulate(eq)).min(),
                RdD=v.sum() / abs((eq - np.maximum.accumulate(eq)).min()),
                streak=mx, P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    print("=" * 128)
    print("MMXM v4 — unswept-pool draw + R:R gate + CE entry.  shorts, skip Monday, "
          "real cost")
    print("  v2 for reference: all-9 PF 1.168 +346R | holdout PF 1.224 +308R")
    print("=" * 128)
    rows = []
    for lab, kw in (("v4 full (ce, pools accum+pd, 2-10R)", {}),
                    ("v4 entry=mt instead of CE", dict(entry_mode="mt")),
                    ("v4 pools = accum only", dict(pools=("accum",))),
                    ("v4 no max_rr", dict(max_rr=None)),
                    ("v4 min_rr 1.0", dict(min_rr=1.0)),
                    ("v4 min_rr 3.0", dict(min_rr=3.0))):
        d = {k: v for k, v in kw.items() if k in ("entry_mode", "pools")}
        x = {k: v for k, v in kw.items() if k in ("min_rr", "max_rr")}
        rows.append(st(book(AL.ALL, **d, **x), f"all 9    {lab}"))
        rows.append(st(book(IDX, hold=True, **d, **x), f"holdout  {lab}"))
    r = pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\mmxm4.csv", index=False)
    print(r.to_string(index=False, float_format=f))
