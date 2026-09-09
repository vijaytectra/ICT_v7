"""Which of the two remaining defects actually produced the PF 1.515 headline?

A  original      ask == bid,  window 360 / hold 1440 bars  (= 90 h / 15 days)
B  quotes only   real ask,    window 360 / hold 1440 bars
C  units only    ask == bid,  window  24 / hold   96 bars  (= the documented 6 h / 24 h)
D  both          real ask,    window  24 / hold   96 bars
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models import screen_fixed as S, fx_lab, ict_system, ict_bt
from models import asia_locked as L, portfolio_locked as P

uni = set(P.UNIVERSE)
VARIANTS = [("A  original (ask=bid, 90h/15d)", False, 360, 1440),
            ("B  real ask only  (90h/15d)",    True,  360, 1440),
            ("C  real order life only",        False, 24,  96),
            ("D  both fixed",                  True,  24,  96)]

print(f"{'variant':32} | {'DEV n':>6} {'DEV PF':>7} {'DEV R':>8} | {'VAL n':>6} {'VAL PF':>7} {'VAL R':>8}")
print("-" * 104)

for label, real_ask, win, hold in VARIANTS:
    frames = []
    for f in sorted(S.SRC.glob("M15_*.csv")):
        sym = f.stem.replace("M15_", "")
        if sym not in uni:
            continue
        try:
            b, spread_px, point = S.load(f)
            if len(b) < 20000:
                continue
            if not real_ask:                       # reproduce the original aliasing
                for k in "ohlc":
                    b[k + "_a"] = b[k + "_b"]
            tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                            (b.l_b - b.c_b.shift()).abs()], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().values
            ctx = ict_system.daily_context(b)
            asia = ict_system.session_pools(b)
            sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)
            kw = dict(L.EXECUTE)
            kw["window_min"] = win
            kw["max_hold"] = hold
            kw["cost"] = 0.4 * spread_px           # the original SPREAD_MULT
            kw["stf_close"] = b.c_b.values
            t = ict_bt.run(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
            if len(t) and L.SKIP_DOW:
                t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
            if len(t):
                t = t.reset_index(drop=True)
                t["sym"] = sym
                frames.append(t)
        except Exception:                          # noqa: BLE001
            continue
    t = pd.concat(frames, ignore_index=True).sort_values("t")
    d, v = fx_lab.split(t)
    print(f"{label:32} | {len(d):6} {fx_lab.pf(d.netR):7.3f} {d.netR.sum():+8.1f} | "
          f"{len(v):6} {fx_lab.pf(v.netR):7.3f} {v.netR.sum():+8.1f}   "
          f"timeouts={int((t.out == 0).sum())}")
