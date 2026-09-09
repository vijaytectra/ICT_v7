"""Why do the six USD majors lose on M1 when the same six are positive on M15?

Three candidate explanations, tested separately:
  PERIOD      M1 is 2024-01..2026-09; the M15 broker dump starts 2022-06.
  COST        M1 uses asia_locked.cost_for(); M15 uses 0.4 x the dump's spread column.
              FX stops here are ~6-7 pips, so a 1-pip difference in the cost assumption
              is ~15% of the risk and moves the CRI gate as well as every trade's P&L.
  RESOLUTION  M15 cannot see the order of events inside a bar.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F, screen_fixed as S, ict_system, asia_locked as L

SIX = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"]
CUT = pd.Timestamp("2024-01-01")


def m15_book(syms, since=None, cost_mode="dump"):
    frames = []
    for sym in syms:
        f = S.SRC / f"M15_{sym}.csv"
        if not f.exists():
            continue
        b, spread_px, point = S.load(f)
        if since is not None:
            b = b[b.index >= since]
        if len(b) < 5000:
            continue
        tr = pd.concat([b.h_b - b.l_b, (b.h_b - b.c_b.shift()).abs(),
                        (b.l_b - b.c_b.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().values
        ctx = ict_system.daily_context(b)
        asia = ict_system.session_pools(b)
        sigs = ict_system.detect(b, b, atr, ctx, asia, **L.DETECT)
        kw = dict(L.EXECUTE)
        kw["window_min"] = 24
        kw["max_hold"] = 96
        if cost_mode == "dump":
            kw["cost"] = 0.4 * spread_px
        else:                                   # the M1 model's own cost, same units
            kw["cost"] = L.cost_for(sym) if sym in L.UNIT else 0.4 * spread_px
        kw["stf_close"] = b.c_b.values
        kw["fill_bar_stop"] = False
        t = F.run_fixed(b, sigs, b.index, 1.0, pd.Timedelta("15min"), **kw)
        if len(t) and L.SKIP_DOW:
            t = t[~t.t.dt.dayofweek.isin(L.SKIP_DOW)]
        if len(t):
            t = t.reset_index(drop=True)
            t["sym"] = sym
            frames.append(t)
    return pd.concat(frames, ignore_index=True).sort_values("t") if frames else pd.DataFrame()


def show(tag, t):
    if not len(t):
        print(f"{tag:44} no trades")
        return
    yrs = max((t.t.max() - t.t.min()).days / 365.25, .01)
    print(f"{tag:44} n={len(t):4} ({len(t)/yrs:5.1f}/yr)  PF={F.pf(t.netR):6.3f}  "
          f"R={t.netR.sum():+8.1f}  WR={(t.netR>0).mean()*100:4.1f}%  "
          f"medRR={t.rr.median():4.2f}  medStop={t.R_pips.median():6.2f}p")


print("=" * 104)
print("1. PERIOD - the same six pairs on M15, whole history vs the M1 window only")
print("=" * 104)
show("M15  2022-06 .. 2026-09", m15_book(SIX))
show("M15  2024-01 .. 2026-09  (M1 window)", m15_book(SIX, since=CUT))
show("M1   2024-01 .. 2026-09", F.book(SIX, fill_bar_stop=False))

print()
print("=" * 104)
print("2. COST - what each model actually charges, in pips, against the median stop")
print("=" * 104)
print(f"{'sym':8} {'M1 cost (pips)':>16} {'M15 dump cost (pips)':>22} {'M1 med stop':>13} {'cost/risk':>10}")
for sym in SIX:
    c_m1 = L.cost_for(sym) / L.UNIT[sym]
    f = S.SRC / f"M15_{sym}.csv"
    b, spread_px, point = S.load(f)
    c_15 = 0.4 * spread_px / L.UNIT[sym]
    t = F.book([sym], fill_bar_stop=False)
    med = t.R_pips.median() if len(t) else np.nan
    print(f"{sym:8} {c_m1:16.3f} {c_15:22.3f} {med:13.2f} {c_m1/med if med==med else np.nan:10.1%}")

print()
print("=" * 104)
print("3. Where the M1 FX loss actually sits - per pair and per side")
print("=" * 104)
t = F.book(SIX, fill_bar_stop=False)
for sym, g in t.groupby("sym"):
    lo, sh = g[g.side == 1].netR, g[g.side == -1].netR
    print(f"{sym:8} n={len(g):3} PF={F.pf(g.netR):6.3f} R={g.netR.sum():+7.2f} | "
          f"long n={len(lo):3} PF={F.pf(lo):6.3f} R={lo.sum():+6.2f} | "
          f"short n={len(sh):3} PF={F.pf(sh):6.3f} R={sh.sum():+6.2f}")

print()
print("outcome mix, M1 FX:")
print(t.out.value_counts().rename({1: "target", -1: "stop", 0: "timeout"}).to_string())
print(f"\nmean win  {t[t.out==1].netR.mean():+.3f} R   mean loss {t[t.out==-1].netR.mean():+.3f} R")
print(f"a 30% win rate at this payoff needs PF = {0.30*t[t.out==1].netR.mean()/(0.70*abs(t[t.out==-1].netR.mean())):.3f}")
