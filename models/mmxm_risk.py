"""Which MMXM negatives are SIGNAL problems and which are PORTFOLIO problems?

The -68 R drawdown and the 25-loss streak were reported as properties of the model.
They may not be.  The book runs up to NINE concurrent positions (one per instrument) at
1 R each, so the account can be 9 R exposed at once and correlated instruments lose
together.  That is a position-sizing choice, not something the signal did.

Measured here, without touching a single rule:
  - drawdown and streak under a cap on concurrent positions
  - the same under 1/N risk scaling
  - whether the yearly decline is real or an artefact of 2026 being a part-year
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as AL
from models.mmxm_final import book

pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"


def with_exit_times(d, hold_min=1440):
    d = d.sort_values("t").reset_index(drop=True).copy()
    d["t_end"] = d.t + pd.to_timedelta(d.bars, unit="m")
    return d


def cap_concurrent(d, cap):
    """Take a trade only if fewer than `cap` positions are open at its entry."""
    d = with_exit_times(d)
    open_ends = []
    keep = []
    for _, r in d.iterrows():
        open_ends = [e for e in open_ends if e > r.t]
        if len(open_ends) < cap:
            keep.append(True); open_ends.append(r.t_end)
        else:
            keep.append(False)
    return d[pd.Series(keep, index=d.index)]


def stat(d, lab, scale=1.0):
    v = d.netR.values * scale
    eq = v.cumsum()
    dd = (eq - np.maximum.accumulate(eq)).min()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    return dict(arm=lab, n=len(v), PF=AL.pf(v), totR=v.sum(), maxDD=dd,
                RdD=v.sum() / abs(dd) if dd else np.nan, streak=mx)


if __name__ == "__main__":
    d = book(AL.ALL, shorts=True, skip_mon=True)
    print("=" * 104)
    print("CONCURRENCY — the -68 R drawdown, re-measured with a cap on open positions")
    print("=" * 104)
    rows = [stat(d, "no cap (9 possible)")]
    for c in (1, 2, 3, 4, 6):
        rows.append(stat(cap_concurrent(d, c), f"max {c} concurrent"))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n  the same books at 1/3 risk per trade (so peak exposure matches):")
    rows = [stat(d, "no cap @ 1/3 R", 1 / 3.0)]
    rows.append(stat(cap_concurrent(d, 3), "max 3 concurrent @ 1 R"))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n" + "=" * 104)
    print("IS THE YEARLY DECLINE REAL, OR IS 2026 A PART-YEAR?")
    print("=" * 104)
    y = d.set_index("t").netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
    y["PF"] = d.set_index("t").netR.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: AL.pf(v.values))
    y["months"] = d.set_index("t").netR.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: (v.index.max() - v.index.min()).days / 30.4)
    y["R_per_month"] = y["sum"] / y["months"]
    y.index = y.index.year
    print(y.to_string(float_format=f))

    print("\n  same three years, but only Jan-Sep so the windows match:")
    dd = d[d.t.dt.month <= 9]
    y2 = dd.set_index("t").netR.groupby(pd.Grouper(freq="YE")).agg(["size", "sum"])
    y2["PF"] = dd.set_index("t").netR.groupby(pd.Grouper(freq="YE")).apply(
        lambda v: AL.pf(v.values))
    y2.index = y2.index.year
    print(y2.to_string(float_format=f))
