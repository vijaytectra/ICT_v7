"""The decisive test for the target question: does a flat R multiple still beat the
dynamic draw-on-liquidity target on NINE YEARS the model has never seen?

The 2024-2026 sweep found flat 3R-4R beating the pool.  A sweep that finds its own
winner proves nothing; this project has died six times that way.  So the same eleven
exits are run, unchanged, on 2015-2023 index data (USA30 / USA500 / USATECH), which
was not used to build, tune or lock anything.

If the ranking holds there, the flat target is real.  If it does not, the locked
dynamic target stays and the 2024-2026 sweep was noise.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import ict_bt, ict_system

HOLD = ["USATECH_H", "USA500_H", "USA30_H"]
f = lambda x: f"{x:.3f}"


_SIG = {}


def _prep(sym):
    """detect() is a Python loop over ~250k M15 bars; run it ONCE per instrument and
    reuse the signals for every exit variant.  Only the executor is cheap to repeat."""
    if sym not in _SIG:
        df = pd.read_parquet(L.DATA / f"{sym}.parquet")
        bars, atr = L.resample(df)
        sigs = ict_system.detect(df, bars, atr, ict_system.daily_context(df),
                                 ict_system.session_pools(df), **L.DETECT)
        _SIG[sym] = (df, bars, sigs)
        print(f"  [{sym}: {len(bars):,} M15 bars, {len(sigs)} signals]", flush=True)
    return _SIG[sym]


def trades_h(sym, shorts_only=False, **over):
    df, bars, sigs = _prep(sym)
    kw = dict(L.EXECUTE)
    kw["cost"] = 1.5                      # index points, same as the locked config
    kw.update(over)
    t = ict_bt.run(df, sigs, bars.index, 1.0, pd.Timedelta(L.TF), **kw)
    if len(t) and shorts_only:
        t = t[t.side == -1].reset_index(drop=True)
    return t


def portfolio_h(shorts_only=False, **over):
    out = []
    for s in HOLD:
        t = trades_h(s, shorts_only, **over)
        if len(t):
            t = t.copy(); t["sym"] = s
            out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


def row(t, label):
    if t is None or len(t) == 0:
        return None
    v = t.netR.values
    eq = t.netR.cumsum()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0
        mx = max(mx, s)
    p, ci = L.bootstrap(v)
    y = t.set_index("t").netR.groupby(pd.Grouper(freq="YE")).sum()
    return dict(exit=label, n=len(t), WR=float((t.out == 1).mean()),
                ER=float(v.mean()), PF=L.pf(v), totR=float(v.sum()),
                maxDD=float((eq - eq.cummax()).min()),
                RdD=float(v.sum() / abs((eq - eq.cummax()).min())), streak=mx,
                pos_yrs=int((y > 0).sum()), n_yrs=len(y), P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    EXITS = [("DYNAMIC pool (LOCKED)", {}),
             ("flat 2.0R", dict(exit_rr=2.0)),
             ("flat 2.5R", dict(exit_rr=2.5)),
             ("flat 3.0R", dict(exit_rr=3.0)),
             ("flat 3.5R", dict(exit_rr=3.5)),
             ("flat 4.0R", dict(exit_rr=4.0)),
             ("flat 5.0R", dict(exit_rr=5.0)),
             ("pool capped 3.0R", dict(cap_rr=3.0)),
             ("pool capped 4.0R", dict(cap_rr=4.0))]

    print("=" * 112)
    print("HOLDOUT 2015-2023, three US indices — data never used to build or lock anything")
    print("=" * 112)
    r = pd.DataFrame([x for x in (row(portfolio_h(**kw), n) for n, kw in EXITS) if x])
    print(r.to_string(index=False, float_format=f))

    print("\n" + "=" * 112)
    print("HOLDOUT, SHORTS ONLY (arm B)")
    print("=" * 112)
    rb = pd.DataFrame([x for x in
                       (row(portfolio_h(shorts_only=True, **kw), n) for n, kw in EXITS)
                       if x])
    print(rb.to_string(index=False, float_format=f))

    print("\n" + "=" * 112)
    print("RANK AGREEMENT — 2024-2026 vs 2015-2023")
    print("=" * 112)
    live = pd.DataFrame([x for x in
                         (row(L.portfolio(**kw), n) for n, kw in EXITS) if x])
    m = live[["exit", "PF"]].merge(r[["exit", "PF"]], on="exit",
                                   suffixes=("_2024_26", "_2015_23"))
    m["rank_new"] = m.PF_2024_26.rank(ascending=False).astype(int)
    m["rank_old"] = m.PF_2015_23.rank(ascending=False).astype(int)
    print(m.to_string(index=False, float_format=f))
    print(f"\n  Spearman rank correlation = "
          f"{m.PF_2024_26.corr(m.PF_2015_23, method='spearman'):+.3f}")
    print(f"  Pearson                    = {m.PF_2024_26.corr(m.PF_2015_23):+.3f}")
