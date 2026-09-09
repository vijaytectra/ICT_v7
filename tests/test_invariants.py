"""Guards that run BEFORE any backtest number is believed.
The v7 sweep-latch bug passed every statistical check; only a code-level
invariant and a per-period signal census can catch that class of error."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from models.unicorn_bt import resample

DATA = pathlib.Path(r"C:\personal\ICT_v7\data")
PAIRS = ["EURUSD","GBPUSD","USDJPY","USDCAD","USDCHF","AUDUSD"]

def census(detect_fn, kw, tf="5min", max_ratio=2.0, min_per_month=5):
    """Signals must be spread evenly across time and across instruments."""
    rows, fails = [], []
    for p in PAIRS:
        df = pd.read_parquet(DATA/f"{p}.parquet"); b, atr = resample(df, tf)
        sg = detect_fn(b.o_b.values, b.h_b.values, b.l_b.values, b.c_b.values, atr, **kw)
        ts = pd.Series([b.index[s["bar"]] for s in sg])
        if len(ts) == 0:
            fails.append(f"{p}: ZERO signals"); continue
        q = ts.dt.to_period("Q").value_counts().sort_index()
        months = (b.index.max() - b.index.min()).days / 30.4
        per_m = len(ts) / months
        empty_q = int((q.reindex(pd.period_range(ts.min(), ts.max(), freq="Q"))
                       .fillna(0) == 0).sum())
        mid = b.index[len(b)//2]
        h1, h2 = int((ts <= mid).sum()), int((ts > mid).sum())
        ratio = h1 / max(h2, 1)
        rows.append(dict(pair=p, n=len(sg), per_month=per_m, first_half=h1,
                         second_half=h2, ratio=ratio, empty_quarters=empty_q,
                         last=ts.max()))
        if ratio > max_ratio or ratio < 1/max_ratio:
            fails.append(f"{p}: half/half ratio {ratio:.1f}x (limit {max_ratio}x)")
        if empty_q: fails.append(f"{p}: {empty_q} quarter(s) with zero signals")
        if per_m < min_per_month: fails.append(f"{p}: only {per_m:.1f} signals/month")
    r = pd.DataFrame(rows)
    if len(r) > 1:
        spread = r.per_month.max() / max(r.per_month.min(), 1e-9)
        if spread > 3.0:
            fails.append(f"cross-pair signal density spread {spread:.1f}x (limit 3x)")
    return r, fails


def no_latched_state(detect_fn, kw, tf="5min"):
    """Every internal timer must be able to expire. Feed a series that makes an
    extreme early and then trends away from it forever: a detector whose sweep
    state latches will fall silent in the second half."""
    n = 40000
    rng = np.random.default_rng(7)
    c = 1.10 + np.cumsum(rng.normal(0, 2e-5, n))
    c[:2000] -= np.linspace(0, 0.02, 2000)          # deep early low
    c[2000:] += np.linspace(0, 0.06, n-2000)        # then up forever
    h = c + np.abs(rng.normal(0, 3e-5, n)); l = c - np.abs(rng.normal(0, 3e-5, n))
    o = np.concatenate([[c[0]], c[:-1]])
    atr = pd.Series(h-l).rolling(14).mean().values
    sg = detect_fn(o, h, l, c, atr, **kw)
    bars = np.array([s["bar"] for s in sg])
    if len(bars) == 0: return ["synthetic series produced ZERO signals"]
    late = int((bars > n*0.6).sum())
    return [] if late > 0 else [f"no signals after 60% of the series ({len(bars)} total) -> state latched"]


if __name__ == "__main__":
    from models.unicorn_v2 import detect
    KW = dict(n=3, max_gap=60, disp_ratio=0.5)
    print("=== GUARD 1: latched-state test (synthetic) ===")
    f1 = no_latched_state(detect, KW)
    print("  PASS" if not f1 else "  FAIL: " + "; ".join(f1))
    print("\n=== GUARD 2: signal census (real data) ===")
    r, f2 = census(detect, KW)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.1f}"))
    print("\n  PASS" if not f2 else "\n  FAIL:\n   - " + "\n   - ".join(f2))
    sys.exit(1 if (f1 or f2) else 0)
