"""Separate the two remaining corrections, on top of D (real ask + real order life).

D   ict_bt.run              short fills on the ASK, covers on the BID  (both favourable)
E   run_fixed, no fill-bar  short fills on the BID, covers on the ASK
F   run_fixed, fill-bar     E + the stop is also checked on the bar the limit filled

E is the one that matters for realism.  F is a conservative upper bound on the fill-bar
blind spot: on a 15-minute bar we cannot know whether the stop came before or after the
fill, so F assumes the worst and E assumes the best.  The truth is between them.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models import screen_fixed as S, fx_lab, ict_system, ict_bt
from models import asia_locked as L, portfolio_locked as P

uni = set(P.UNIVERSE)


def build(sym, f):
    b, spread_px, point = S.load(f)
    if len(b) < 20000:
        return None
    tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                    (b.l_b - b.c_b.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().values
    ctx = ict_system.daily_context(b)
    asia = ict_system.session_pools(b)
    sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)
    kw = dict(L.EXECUTE)
    kw["window_min"] = 24
    kw["max_hold"] = 96
    kw["cost"] = 0.4 * spread_px
    kw["stf_close"] = b.c_b.values
    return b, sigs, kw, point


def sweep(engine, label, **extra):
    frames = []
    for f in sorted(S.SRC.glob("M15_*.csv")):
        sym = f.stem.replace("M15_", "")
        if sym not in uni:
            continue
        try:
            got = build(sym, f)
            if got is None:
                continue
            b, sigs, kw, point = got
            kw = dict(kw)
            kw.update(extra)
            t = engine(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
            if len(t) and L.SKIP_DOW:
                t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
            if len(t):
                t = t.reset_index(drop=True)
                t["sym"] = sym
                frames.append(t)
        except Exception:                                   # noqa: BLE001
            continue
    t = pd.concat(frames, ignore_index=True).sort_values("t")
    d, v = fx_lab.split(t)
    print(f"{label:38} | {len(d):5} {fx_lab.pf(d.netR):6.3f} {d.netR.sum():+8.1f} | "
          f"{len(v):5} {fx_lab.pf(v.netR):6.3f} {v.netR.sum():+8.1f}")
    return t


print(f"{'variant':38} | {'DEVn':>5} {'DEVPF':>6} {'DEV R':>8} | {'VALn':>5} {'VALPF':>6} {'VAL R':>8}")
print("-" * 100)
sweep(ict_bt.run, "D  short favoured on both legs")
tE = sweep(fx_lab.run_fixed, "E  short pays spread, no fill-bar", fill_bar_stop=False)
tF = sweep(fx_lab.run_fixed, "F  E + fill-bar stop (worst case)", fill_bar_stop=True)

print()
for name, t in (("E", tE), ("F", tF)):
    lo = t[t.side == 1].netR
    sh = t[t.side == -1].netR
    print(f"{name}  longs  n={len(lo):5} PF={fx_lab.pf(lo):6.3f} R={lo.sum():+8.1f}   "
          f"shorts n={len(sh):5} PF={fx_lab.pf(sh):6.3f} R={sh.sum():+8.1f}")

print()
print("Per-instrument, variant E, positive in BOTH halves:")
ps = S.per_symbol(tE)
both = ps[(ps.PF_dev > 1.0) & (ps.PF_val > 1.0)]
print(both.to_string(index=False, float_format=lambda x: f"{x:7.3f}"))
tE.to_csv(r"C:\personal\ICT_v7\reports\isolate_E_trades.csv", index=False)
