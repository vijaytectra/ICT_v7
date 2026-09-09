"""TEST 15 — shadow-execution parity.  The research engine vs the MT5 EA, same data.

Both engines are pointed at the SAME USTEC M15 series the broker gave the tester, and
their signals are compared one by one.  A backtest that agrees with itself proves
nothing; the only thing that matters is whether the code that will trade produces the
same setups as the code that was researched.

The M1 history the terminal holds is only ~3 months, so execution parity can only be
checked on the tail.  DETECTION parity is checked over the whole 2022-2026 run, and
detection is where a port goes wrong.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import ict_system

T2 = (r"C:\Users\Vijayakumar R\AppData\Roaming\MetaQuotes\Terminal"
      r"\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files")


def load_m15():
    d = pd.read_csv(fr"{T2}\USTEC_M15.csv")
    d["t"] = pd.to_datetime(d.t, format="%Y.%m.%d %H:%M:%S")
    d = d.set_index("t").sort_index()
    d.columns = ["o_b", "h_b", "l_b", "c_b"]
    for c in ["o_a", "h_a", "l_a", "c_a"]:
        d[c] = d[c.replace("_a", "_b")]
    return d


def asia_from_m15(bars, a0=2, a1=9):
    """The EA reads the Asian range in BROKER SERVER hours; ICMarkets server is
    EET/EEST, which is what the research data is stamped in.  Same window, so the
    comparison is apples to apples."""
    h = bars.index.hour
    sel = bars[(h >= a0) & (h < a1)]
    g = sel.groupby(sel.index.normalize())
    return pd.DataFrame({"ah": g.h_b.max(), "al": g.l_b.min()})


def daily_from_m15(bars):
    d = bars.resample("1D").agg({"o_b": "first", "h_b": "max",
                                 "l_b": "min", "c_b": "last"}).dropna()
    hi, hp, lo, lp = ict_system.swings(d.h_b.values, d.l_b.values, 2)
    c = d.c_b.values
    bias = np.zeros(len(d)); last_hi = last_lo = np.nan; cur = 0
    for i in range(len(d)):
        if hi[i]: last_hi = hp[i]
        if lo[i]: last_lo = lp[i]
        if np.isfinite(last_hi) and c[i] > last_hi: cur = 1
        elif np.isfinite(last_lo) and c[i] < last_lo: cur = -1
        bias[i] = cur
    rng = (d.h_b - d.l_b).rolling(20).mean()
    move = (d.c_b - d.c_b.shift(20)).abs()
    prof = (move / (rng * 20) > 0.18).astype(int)
    return pd.DataFrame({"bias": bias, "trending": prof.values,
                         "pdh": d.h_b.values, "pdl": d.l_b.values},
                        index=d.index).shift(1)


def python_raids(bars, asia, n=5):
    """Every raid the research detector would register, with its own reference."""
    idx = bars.index
    h, l = bars.h_b.values, bars.l_b.values
    hi, hp, lo, lp = ict_system.swings(h, l, n)
    A = asia.reindex(idx.normalize()).values
    hour = idx.hour
    out = []
    sh = sl = np.nan
    for i in range(n + 4, len(idx)):
        if hi[i]: sh = hp[i]
        if lo[i]: sl = lp[i]
        if hour[i] < 9: continue
        ah, al = A[i]
        if np.isfinite(al) and l[i] < al <= l[i-1]:
            out.append(dict(t=idx[i], side=1, px=l[i], asia=al, ref=sh))
        if np.isfinite(ah) and h[i] > ah >= h[i-1]:
            out.append(dict(t=idx[i], side=-1, px=h[i], asia=ah, ref=sl))
    return pd.DataFrame(out)


if __name__ == "__main__":
    bars = load_m15()
    print(f"broker M15: {len(bars)} bars  {bars.index.min()} -> {bars.index.max()}")
    asia = asia_from_m15(bars)
    py = python_raids(bars, asia)
    ea = pd.read_csv("reports/ea_ustec_signals.csv", parse_dates=["t"])
    ear = ea[ea.kind == "RAID"].copy()

    lo, hi = ear.t.min(), ear.t.max()
    py = py[(py.t >= lo) & (py.t <= hi)]
    print(f"\nEA raids     {len(ear)}")
    print(f"Python raids {len(py)}   (same window {lo} -> {hi})")

    k_ea = set(zip(ear.t, ear.side))
    k_py = set(zip(py.t, py.side))
    both = k_ea & k_py
    print(f"\n  matched on (timestamp, side): {len(both)}")
    print(f"  EA only     : {len(k_ea - k_py)}")
    print(f"  Python only : {len(k_py - k_ea)}")
    print(f"  agreement   : {len(both)/max(len(k_ea|k_py),1)*100:.1f}%")

    m = ear.merge(py, on=["t", "side"], suffixes=("_ea", "_py"))
    if len(m):
        for c in ("px", "asia", "ref"):
            d = (m[f"{c}_ea"] - m[f"{c}_py"]).abs()
            print(f"  {c:5s} identical: {(d < 1e-6).mean()*100:5.1f}%   "
                  f"median |diff| {d.median():.4f}   max {d.max():.2f}")
    miss = sorted(k_py - k_ea)[:5]
    extra = sorted(k_ea - k_py)[:5]
    if miss:  print("\n  first Python-only:", [str(x[0]) for x in miss])
    if extra: print("  first EA-only    :", [str(x[0]) for x in extra])
