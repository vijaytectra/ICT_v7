"""Everything recomputed on the broker's real cost schedule.

Old model : flat 1.5 index points / 0.8 FX pips - a different real cost on every
            instrument, because the quote units are not comparable.
New model : IC Markets Raw Spread, verified.  FX USD 7.00 per lot round trip converted
            through each pair's own pip value; indices commission-free.  Plus a declared
            slippage allowance as a multiple of each instrument's own spread.

SLIP_MULT is the one number that is NOT measured, so it is swept rather than assumed.
"""
import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L

pd.set_option("display.width", 215); f = lambda x: f"{x:.3f}"


def full(d, lab):
    if d is None or len(d) < 20:
        return dict(arm=lab, n=0 if d is None else len(d))
    v = d.netR.values; eq = v.cumsum(); p, ci = L.bootstrap(v)
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0; mx = max(mx, s)
    i, o = d[d.t < L.IS_END], d[d.t >= L.IS_END]
    return dict(arm=lab, n=len(v), WR=float((d.out == 1).mean()), ER=v.mean(),
                PF=L.pf(v), totR=v.sum(),
                maxDD=(eq - np.maximum.accumulate(eq)).min(), streak=mx,
                is_PF=L.pf(i.netR.values) if len(i) else np.nan,
                oos_PF=L.pf(o.netR.values) if len(o) else np.nan,
                P_edge=p, ci_lo=ci[0])


if __name__ == "__main__":
    print("=" * 130)
    print("SLIPPAGE SENSITIVITY — commission is measured, slippage is not, so it is swept")
    print("=" * 130)
    rows = []
    for sm in (0.0, 0.25, 0.5, 1.0, 1.5):
        L.SLIP_MULT = sm
        L._prep = {}                      # cost feeds the CRI gate, so signals change
        for arm, sh in (("A", False), ("B", True)):
            d = L.portfolio(shorts_only=sh)
            r = full(d, f"ARM {arm}  slip {sm:.2f}x spread")
            r["cost_eurusd"] = L.cost_for("EURUSD")
            r["cost_ustec"] = L.cost_for("USATECH")
            rows.append(r)
    r = pd.DataFrame(rows)
    r.to_csv(r"C:\personal\ICT_v7\reports\recost_slip.csv", index=False)
    print(r.to_string(index=False, float_format=f))

    L.SLIP_MULT = 0.5
    print("\n" + "=" * 130)
    print("HEADLINE at SLIP_MULT = 0.5   (half a spread of slippage per round trip)")
    print("=" * 130)
    rows = []
    for arm, sh in (("A", False), ("B", True)):
        d = L.portfolio(shorts_only=sh)
        rows.append(full(d, f"ARM {arm} live 2024-26"))
        d.to_csv(rf"C:\personal\ICT_v7\reports\recost_arm{arm}.csv", index=False)
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\nPER INSTRUMENT, Arm A")
    d = L.portfolio()
    g = d.groupby("sym").agg(n=("netR", "size"), WR=("out", lambda v: (v == 1).mean()),
                             PF=("netR", lambda v: L.pf(v.values)),
                             totR=("netR", "sum"), med_stop=("R_pips", "median"))
    g["cost"] = [L.cost_for(s) for s in g.index]
    g["cost_pct_of_risk"] = g.cost / g.med_stop * 100
    print(g.sort_values("PF", ascending=False).to_string(float_format=f))
