"""Guards for MMXM v2.  Same three as v1, plus one new one for the SMT wiring:
a peer's sweep clock must never be readable before that peer's bar has closed.
"""
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm2, mmxm2_lab

DET = dict(n=5, require_contraction=False, require_smt=True, require_judas=True,
           require_bias=False, target_mode="accum")


def guard_latched():
    n = 30000
    rng = np.random.default_rng(7)
    c = 100.0 + np.cumsum(rng.normal(0, 0.02, n))
    c[:2000] -= np.linspace(0, 20, 2000)
    c[2000:] += np.linspace(0, 60, n - 2000)
    h = c + np.abs(rng.normal(0, 0.03, n)); l = c - np.abs(rng.normal(0, 0.03, n))
    o = np.concatenate([[c[0]], c[:-1]])
    idx = pd.date_range("2024-01-01", periods=n, freq="15min")
    bars = pd.DataFrame({"o_b": o, "h_b": h, "l_b": l, "c_b": c}, index=idx)
    acc = mmxm2.accumulation(bars)
    sg = mmxm2.detect(bars, acc, **{**DET, "require_smt": False})
    if not sg:
        return ["synthetic series produced ZERO signals"]
    b = np.array([s["bar"] for s in sg])
    return [] if (b > n * 0.6).sum() else ["no signals after 60% -> state latched"]


def guard_prefix(sym="USATECH", tf="15min", cut=0.6):
    """Whole pipeline on a prefix vs on the full data, SMT peers included."""
    fails = []
    full = mmxm2_lab.signals(sym, tf, **DET)
    _, bf, _, _, _, _ = mmxm2_lab.prep(sym, tf)

    df = mmxm2_lab.load(sym)
    m = int(len(df) * cut)
    dfp = df.iloc[:m]
    bp, _ = mmxm2_lab.resample(dfp, tf)
    accp = mmxm2.accumulation(bp)
    pr = {}
    for p in mmxm2_lab.GROUPS[mmxm2_lab.GROUP_OF[sym]]:
        if p == sym:
            continue
        d2 = mmxm2_lab.load(p)
        d2 = d2[d2.index <= dfp.index[-1]]
        b2, _ = mmxm2_lab.resample(d2, tf)
        a2 = mmxm2.accumulation(b2)
        pr[p] = mmxm2.sweep_clock(b2, a2).reindex(bp.index, method="ffill").fillna(False)
    from models import mmxm
    ctxp, _ = mmxm.htf_context(dfp, "1D", 2)
    sp = mmxm2.detect(bp, accp, peers=pr, htf_bias=ctxp.bias, **DET)

    keyf = {(bf.index[s["bar"]], s["side"]): s for s in full}
    checked = 0
    for s in sp:
        t = bp.index[s["bar"]]
        if t > bp.index[-1] - pd.Timedelta("2D"):
            continue
        checked += 1
        k = (t, s["side"])
        if k not in keyf:
            fails.append(f"signal {t} side {s['side']} vanishes when data is appended")
            continue
        f = keyf[k]
        for fld in ("sweep_px", "zone_lo", "zone_hi", "cisd", "target"):
            if not np.isclose(s[fld], f[fld], rtol=0, atol=1e-9, equal_nan=True):
                fails.append(f"{t} {fld}: prefix {s[fld]} != full {f[fld]}")
    if checked == 0:
        fails.append("prefix run produced no comparable signals")
    return fails[:8], checked


def guard_accumulation_window(sym="USATECH", tf="15min"):
    """No signal may be emitted before its own accumulation window has closed, and
    the accumulation bounds must come only from bars inside that window."""
    _, bars, _, acc, _, _ = mmxm2_lab.prep(sym, tf)
    sg = mmxm2_lab.signals(sym, tf, **DET)
    fails = []
    for s in sg[:400]:
        t = bars.index[s["bar"]]
        if t.hour < mmxm2.A_WIN[1]:
            fails.append(f"{t} emitted before the accumulation window closed")
        d = t.normalize()
        w = bars[(bars.index.normalize() == d) & (bars.index.hour >= mmxm2.A_WIN[0])
                 & (bars.index.hour < mmxm2.A_WIN[1])]
        if len(w) and not (np.isclose(s["acc_lo"], w.l_b.min())
                           and np.isclose(s["acc_hi"], w.h_b.max())):
            fails.append(f"{t} accumulation bounds do not match the A window")
    return fails[:5]


def guard_census(syms, tf="15min"):
    rows, fails = [], []
    for p in syms:
        _, bars, _, _, _, _ = mmxm2_lab.prep(p, tf)
        sg = mmxm2_lab.signals(p, tf, **DET)
        if not sg:
            fails.append(f"{p}: ZERO signals"); continue
        ts = pd.Series([bars.index[s["bar"]] for s in sg])
        months = (bars.index.max() - bars.index.min()).days / 30.4
        fq = pd.period_range(bars.index.min(), bars.index.max(), freq="Q")
        empty = int((ts.dt.to_period("Q").value_counts().reindex(fq).fillna(0) == 0).sum())
        mid = bars.index[len(bars) // 2]
        h1, h2 = int((ts <= mid).sum()), int((ts > mid).sum())
        rows.append(dict(sym=p, n=len(sg), per_month=len(sg) / months,
                         first_half=h1, second_half=h2, ratio=h1 / max(h2, 1),
                         empty_q=empty, last=ts.max()))
        if empty:
            fails.append(f"{p}: {empty} empty quarter(s)")
        if not 0.4 <= h1 / max(h2, 1) <= 2.5:
            fails.append(f"{p}: half/half ratio {h1/max(h2,1):.2f}")
    return pd.DataFrame(rows), fails


if __name__ == "__main__":
    print("=== GUARD 1: latched state ===")
    f1 = guard_latched(); print("  PASS" if not f1 else "  FAIL: " + "; ".join(f1))
    print("\n=== GUARD 2: prefix invariance (incl. SMT peers) ===")
    f2, ch = guard_prefix(); print(f"  {ch} signals compared")
    print("  PASS" if not f2 else "  FAIL:\n   - " + "\n   - ".join(f2))
    print("\n=== GUARD 3: accumulation-window causality ===")
    f3 = guard_accumulation_window()
    print("  PASS" if not f3 else "  FAIL:\n   - " + "\n   - ".join(f3))
    print("\n=== GUARD 4: signal census ===")
    r, f4 = guard_census(mmxm2_lab.INDICES + mmxm2_lab.FX)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print("\n  PASS" if not f4 else "\n  FAIL:\n   - " + "\n   - ".join(f4))
    sys.exit(1 if (f1 or f2 or f3 or f4) else 0)
