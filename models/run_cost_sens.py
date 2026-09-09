"""How much of the result is the cost assumption?

The broker dump's `spread` column is unreliable: 95.2% zeros on EURUSD, but a mean of
123.5 points on USTEC (12.3 index points at a 0.1 point size), which is far wider than
IC Markets' published raw index spread.  MT5 writes this field per bar and it widens
heavily outside the cash session - which is exactly when this model trades.

So rather than assert one number, sweep the multiplier and show where the sign flips.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models import screen_fixed as S, fx_lab, portfolio_locked as P

pd.set_option("display.width", 200)
uni = set(P.UNIVERSE)

print("cost = MULT x (mean non-zero spread) + commission,  on the locked 33")
print("=" * 100)
print(f"{'MULT':>6} | {'DEV n':>6} {'DEV PF':>7} {'DEV R':>8} | {'VAL n':>6} {'VAL PF':>7} {'VAL R':>8}")
print("-" * 100)

rows = []
for mult in (0.0, 0.25, 0.5, 0.75, 1.0):
    frames = []
    for f in sorted(S.SRC.glob("M15_*.csv")):
        sym = f.stem.replace("M15_", "")
        if sym not in uni:
            continue
        try:
            b, spread_px, point = S.load(f)
            if len(b) < 20000:
                continue
            tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                            (b.l_b - b.c_b.shift()).abs()], axis=1).max(1)
            atr = tr.rolling(14).mean().values
            from models import ict_system, asia_locked as L
            ctx = ict_system.daily_context(b)
            asia = ict_system.session_pools(b)
            sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)
            kw = dict(L.EXECUTE)
            kw["window_min"] = 24
            kw["max_hold"] = 96
            kw["cost"] = mult * spread_px + S.commission_px(sym, float(b.c_b.iloc[-1]), point)
            kw["stf_close"] = b.c_b.values
            t = fx_lab.run_fixed(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
            if len(t) and L.SKIP_DOW:
                t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
            if len(t):
                t = t.reset_index(drop=True)
                t["sym"] = sym
                frames.append(t)
        except Exception:                                    # noqa: BLE001
            continue
    t = pd.concat(frames, ignore_index=True).sort_values("t")
    d, v = fx_lab.split(t)
    print(f"{mult:6.2f} | {len(d):6} {fx_lab.pf(d.netR):7.3f} {d.netR.sum():+8.1f} | "
          f"{len(v):6} {fx_lab.pf(v.netR):7.3f} {v.netR.sum():+8.1f}")
    rows.append((mult, len(d), fx_lab.pf(d.netR), d.netR.sum(),
                 len(v), fx_lab.pf(v.netR), v.netR.sum()))

print()
print("MULT 0.00 = commission only, no spread at all - the most generous case that is")
print("still not the original bug (the original also had ask == bid inside the fills).")
