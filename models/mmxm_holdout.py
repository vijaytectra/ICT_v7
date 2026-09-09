"""MMXM shorts + skip Monday on the 2015-2023 holdout.

The MMXM work only ever touched 2024-2026.  The Asian-range model earned its lock partly
on a nine-year holdout; MMXM has never seen one.  Without this, a PF of 1.168 is a
single-period result from a model with 381 configurations of search history behind it.

Limitation stated up front: the holdout is INDEX data only, and MMXM's edge sits in FX
(FX PF 1.222, indices 1.066).  So this tests the weaker half.  It is still the only
out-of-period evidence available.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as AL
from models import mmxm, mmxm2, mmxm_bt
from models.mmxm_final import DET, EXE

pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"
HOLD = [("USATECH", "USATECH_H"), ("USA500", "USA500_H"), ("USA30", "USA30_H")]
_C = {}


def prep(path, tf="15min"):
    if path not in _C:
        df = pd.read_parquet(AL.DATA / f"{path}.parquet")
        bars, atr = AL.resample(df)
        acc = mmxm2.accumulation(bars, mmxm2.A_WIN)
        ctx, _ = mmxm.htf_context(df, "1D", 2)
        _C[path] = (df, bars, acc, ctx.bias)
    return _C[path]


def book(mult=1.0):
    out = []
    for sym, path in HOLD:
        df, bars, acc, bias = prep(path)
        sigs = mmxm2.detect(bars, acc, peers=None, htf_bias=bias, **DET)
        e = dict(EXE); e["cost"] = 1.5 * mult
        if e["cost"] == 0:
            e.pop("max_cost_frac", None)
        t = mmxm_bt.run(df, sigs, bars.index, 1.0, pd.Timedelta("15min"), **e)
        if not len(t):
            continue
        t = t[(t.t.dt.dayofweek != 0) & (t.side == -1)]
        if len(t):
            t = t.copy(); t["sym"] = sym; out.append(t)
    return pd.concat(out).sort_values("t").reset_index(drop=True) if out else pd.DataFrame()


if __name__ == "__main__":
    print("=" * 104)
    print("MMXM shorts + skip Monday — 2015-2023 HOLDOUT (indices only)")
    print("  for reference, 2024-2026 indices at full charge: n=897 PF 1.066 "
          "P(edge) 0.747")
    print("=" * 104)
    print(f"{'cost mult':>10}{'n':>7}{'WR':>7}{'PF':>8}{'totR':>10}{'maxDD':>9}"
          f"{'R/DD':>7}{'streak':>8}{'P(edge)':>9}{'ci_lo':>8}")
    for m in (0.0, 0.5, 1.0, 1.5):
        d = book(m)
        if len(d) < 25:
            continue
        v = d.netR.values; eq = v.cumsum()
        dd = (eq - np.maximum.accumulate(eq)).min()
        s = mx = 0
        for x in v:
            s = s + 1 if x <= 0 else 0; mx = max(mx, s)
        p, ci = mmxm_bt.bootstrap(d)
        print(f"{m:>10.2f}{len(v):>7}{(v>0).mean():>7.3f}{AL.pf(v):>8.3f}{v.sum():>+10.1f}"
              f"{dd:>9.1f}{v.sum()/abs(dd):>7.2f}{mx:>8}{p:>9.3f}{ci[0]:>+8.3f}")

    d = book(1.0)
    d.to_csv(r"C:\personal\ICT_v7\reports\mmxm_holdout.csv", index=False)
    print("\nPER INSTRUMENT, full charge")
    r = d.groupby("sym").agg(n=("netR", "size"), WR=("netR", lambda v: (v > 0).mean()),
                             PF=("netR", lambda v: AL.pf(v.values)),
                             totR=("netR", "sum"))
    print(r.to_string(float_format=f))

    print("\nPER YEAR, full charge")
    y = d.set_index("t").netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
    y["PF"] = d.set_index("t").netR.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: AL.pf(v.values))
    y.index = y.index.year
    print(y.to_string(float_format=f))
    print(f"\n  positive years {(y['sum']>0).sum()} of {len(y)}")
