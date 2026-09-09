"""Guards that run BEFORE any MMXM backtest number is believed.

The v7 Unicorn sweep-latch bug passed every statistical check.  Only a code-level
invariant plus a per-period signal census catches that class of error, so all three
guards below must pass before a single profit factor is quoted.

  GUARD 1  latched state  - every internal timer must be able to expire
  GUARD 2  prefix invariance - a signal emitted at bar i must not change when bars
                              after i are appended.  This is the causality proof.
  GUARD 3  signal census  - signals evenly spread across quarters and instruments
"""
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm, mmxm_lab

DET = dict(n=5, poi_mode="fvg", sweep_pool="swing", require_bias=True,
           require_discount=True, max_gap=40)


# ------------------------------------------------------------------ GUARD 1
def guard_latched(det=DET):
    """A series that makes an extreme early then trends away from it forever.
    A detector whose phase state latches falls silent in the second half."""
    n = 30000
    rng = np.random.default_rng(7)
    c = 100.0 + np.cumsum(rng.normal(0, 0.02, n))
    c[:2000] -= np.linspace(0, 20, 2000)
    c[2000:] += np.linspace(0, 60, n - 2000)
    h = c + np.abs(rng.normal(0, 0.03, n))
    l = c - np.abs(rng.normal(0, 0.03, n))
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-01-01", periods=n, freq="15min")
    bars = pd.DataFrame({"o_b": o, "h_b": h, "l_b": l, "c_b": c}, index=idx)
    df = bars.copy()
    ctx, fvgs = mmxm.htf_context(df, "4h", 2, 60)
    sg = mmxm.detect(bars, ctx, fvgs, **det)
    if not sg:
        return ["synthetic series produced ZERO signals"]
    bars_at = np.array([s["bar"] for s in sg])
    late = int((bars_at > n * 0.6).sum())
    return [] if late > 0 else [
        f"no signals after 60% of the series ({len(sg)} total) -> state latched"]


# ------------------------------------------------------------------ GUARD 2
def guard_prefix(sym="USATECH", tf="15min", htf="4h", det=DET, cut=0.6):
    """Run the whole pipeline on a PREFIX of the data and on the full data.
    Every signal the prefix run emits must appear identically in the full run."""
    df = mmxm_lab.load(sym)
    m = int(len(df) * cut)
    dfp = df.iloc[:m]

    def go(d):
        bars, atr = mmxm_lab.resample(d, tf)
        ctx, fvgs = mmxm.htf_context(d, htf, 2, 60)
        return bars, mmxm.detect(bars, ctx, fvgs, atr=atr, **det)

    bp, sp = go(dfp)
    bf, sf = go(df)
    keyf = {(bf.index[s["bar"]], s["side"]): s for s in sf}
    fails = []
    checked = 0
    for s in sp:
        t = bp.index[s["bar"]]
        if t > bp.index[-1] - pd.Timedelta("2D"):
            continue                            # edge of the prefix, legitimately open
        checked += 1
        k = (t, s["side"])
        if k not in keyf:
            fails.append(f"signal at {t} side {s['side']} vanishes when data is appended")
            continue
        f = keyf[k]
        for fld in ("sweep_px", "zone_lo", "zone_hi", "cisd"):
            if not np.isclose(s[fld], f[fld], rtol=0, atol=1e-9):
                fails.append(f"{t} {fld}: prefix {s[fld]} != full {f[fld]}")
    if checked == 0:
        fails.append("prefix run produced no comparable signals")
    return fails[:8], checked


# ------------------------------------------------------------------ GUARD 3
def guard_census(syms, det=DET, tf="15min", htf="4h", max_ratio=2.5, min_per_month=1.0):
    rows, fails = [], []
    for p in syms:
        _, bars, _, _, _ = mmxm_lab.prep(p, tf, htf)
        sg = mmxm_lab.signals(p, tf, htf, **det)
        if not sg:
            fails.append(f"{p}: ZERO signals"); continue
        ts = pd.Series([bars.index[s["bar"]] for s in sg])
        months = (bars.index.max() - bars.index.min()).days / 30.4
        q = ts.dt.to_period("Q").value_counts()
        full_q = pd.period_range(bars.index.min(), bars.index.max(), freq="Q")
        empty_q = int((q.reindex(full_q).fillna(0) == 0).sum())
        mid = bars.index[len(bars) // 2]
        h1, h2 = int((ts <= mid).sum()), int((ts > mid).sum())
        ratio = h1 / max(h2, 1)
        rows.append(dict(sym=p, n=len(sg), per_month=len(sg) / months,
                         first_half=h1, second_half=h2, ratio=ratio,
                         empty_q=empty_q, last=ts.max()))
        if ratio > max_ratio or ratio < 1 / max_ratio:
            fails.append(f"{p}: half/half ratio {ratio:.2f}x (limit {max_ratio}x)")
        if empty_q:
            fails.append(f"{p}: {empty_q} quarter(s) with zero signals")
        if len(sg) / months < min_per_month:
            fails.append(f"{p}: only {len(sg)/months:.1f} signals/month")
    return pd.DataFrame(rows), fails


if __name__ == "__main__":
    print("=== GUARD 1: latched-state (synthetic) ===")
    f1 = guard_latched()
    print("  PASS" if not f1 else "  FAIL: " + "; ".join(f1))

    print("\n=== GUARD 2: prefix invariance / causality (USATECH) ===")
    f2, checked = guard_prefix()
    print(f"  {checked} signals compared")
    print("  PASS" if not f2 else "  FAIL:\n   - " + "\n   - ".join(f2))

    print("\n=== GUARD 3: signal census ===")
    r, f3 = guard_census(mmxm_lab.INDICES + mmxm_lab.FX)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n  PASS" if not f3 else "\n  FAIL:\n   - " + "\n   - ".join(f3))

    sys.exit(1 if (f1 or f2 or f3) else 0)
