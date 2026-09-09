"""The final configuration: instruments chosen on DEV, read once on VAL.

The operator's target is PF > 2 at 1-2 trades a week with a dynamic minimum 2R.  Three
of those four are available in this data; the fourth (a 70-80% win rate) is not, and the
barrier-race work established why - p(+2R before -1R) sits on 1/3 for every stop
placement tested, in both periods.

So the lever that remains is the one ASIA_PF_REVIEW.md already identified: WHICH
INSTRUMENTS the model runs on.  That is decidable without touching a rule, and it is
decidable on DEV alone.

  DEV  US indices 2015-2023  (nine years, the only long history in the project)
  VAL  everything 2024-2026  (read once, after the selection is fixed)

SELECTION RULE, fixed before looking at VAL:  keep an instrument if its DEV profit
factor is above 1.20.  FX has no history before 2024, so no FX pair can be selected this
way - they are reported separately and are NOT part of the locked set.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models import ict_bt, ict_system

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"
DEV_PF_FLOOR = 1.20
_C = {}


def data(sym, hold):
    k = (sym, hold)
    if k not in _C:
        p = sym + "_H" if hold else sym
        df = pd.read_parquet(L.DATA / f"{p}.parquet")
        bars, atr = L.resample(df)
        _C[k] = (df, bars, atr, ict_system.daily_context(df),
                 ict_system.session_pools(df))
    return _C[k]


def book(syms, hold):
    out = []
    for s in syms:
        df, bars, atr, ctx, asia = data(s, hold)
        sigs = ict_system.detect(df, bars, atr, ctx, asia, **L.DETECT)
        kw = dict(L.EXECUTE); kw["cost"] = L.cost_for(s, hold)
        t = ict_bt.run(df, sigs, bars.index, L.UNIT[s], pd.Timedelta(L.TF), **kw)
        if not len(t):
            continue
        t = t[~t.t.dt.dayofweek.isin([0])]
        if len(t):
            t = t.copy(); t["sym"] = s; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def stat(d, lab, months):
    if d is None or len(d) < 10:
        return dict(arm=lab, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = L.bootstrap(v)
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    w = d[d.out == 1].netR; ls = d[d.out == -1].netR
    return dict(arm=lab, n=len(v), per_wk=len(v) / (months * 4.33),
                WR=float((d.out == 1).mean()), avg_win=w.mean(), avg_loss=ls.mean(),
                avg_rr=d.rr.mean(), ER=v.mean(), PF=L.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(),
                RdD=v.sum() / abs((eq - np.maximum.accumulate(eq)).min()),
                streak=mx, P_edge=p, ci_lo=ci[0], ci_hi=ci[1])


if __name__ == "__main__":
    print("=" * 128)
    print("STEP 1 — SELECTION, on DEV only (US indices 2015-2023).  Keep PF > 1.20.")
    print("=" * 128)
    dev = book(L.INDICES, True)
    rows = []
    for s in L.INDICES:
        rows.append(stat(dev[dev.sym == s], s, 108))
    r = pd.DataFrame(rows)
    print(r[["arm", "n", "per_wk", "WR", "PF", "totR", "maxDD"]]
          .to_string(index=False, float_format=f))
    keep = [x["arm"] for x in rows if x.get("PF", 0) > DEV_PF_FLOOR]
    print(f"\n  SELECTED (DEV PF > {DEV_PF_FLOOR}): {keep}")
    print(f"  dropped: {[s for s in L.INDICES if s not in keep]}")

    print("\n" + "=" * 128)
    print("STEP 2 — the selected set, everywhere.  Nothing re-tuned.")
    print("=" * 128)
    rows = []
    rows.append(stat(book(keep, True), f"DEV  2015-2023  {'+'.join(keep)}", 108))
    rows.append(stat(book(keep, False), f"VAL  2024-2026  {'+'.join(keep)}", 32))
    allp = pd.concat([book(keep, True), book(keep, False)]).sort_values("t")
    rows.append(stat(allp, f"BOTH 2015-2026  {'+'.join(keep)}", 140))
    rows.append(stat(book(L.INDICES, True), "DEV  all three indices", 108))
    rows.append(stat(book(L.INDICES, False), "VAL  all three indices", 32))
    rows.append(stat(book(L.ALL, False), "VAL  all nine (locked today)", 32))
    r2 = pd.DataFrame(rows)
    r2.to_csv(r"C:\personal\ICT_v7\reports\final_config.csv", index=False)
    print(r2.to_string(index=False, float_format=f))
    allp.to_csv(r"C:\personal\ICT_v7\reports\final_trades.csv", index=False)

    print("\n" + "=" * 128)
    print("STEP 3 — the selected set, per year, 12 years, rules frozen")
    print("=" * 128)
    y = allp.set_index("t").netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
    y["PF"] = allp.set_index("t").netR.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: L.pf(v.values))
    y["WR"] = allp.set_index("t").out.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: (v == 1).mean())
    y.index = y.index.year
    print(y.to_string(float_format=f))
    print(f"\n  positive years {(y['sum'] > 0).sum()} of {len(y)}")
