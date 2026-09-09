"""Win / loss breakdown for any exit variant.  Read-only; changes nothing.

    python models/breakdown.py                  the locked dynamic target
    python models/breakdown.py --exit 2         gated flat 2R
    python models/breakdown.py --exit 4 --short arm B, flat 4R
    python models/breakdown.py --cap 4          pool capped at 4R
    python models/breakdown.py --all            every variant, side by side

The `out` column of a trade frame is the whole story:
    out =  1  target hit          -> win
    out = -1  stop hit            -> loss
    out =  0  24 h timeout        -> flat exit, small win or small loss
"""
import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L

f = lambda x: f"{x:.3f}"


def breakdown(t, label):
    v = t.netR.values
    tp, sl, to = (t.out == 1), (t.out == -1), (t.out == 0)
    gross_w = v[v > 0].sum()
    gross_l = -v[v < 0].sum()
    return dict(
        variant=label, n=len(t),
        WIN=int(tp.sum()), LOSS=int(sl.sum()), TIMEOUT=int(to.sum()),
        win_pct=float(tp.mean()),
        avg_win=float(v[tp].mean()) if tp.any() else np.nan,
        avg_loss=float(v[sl].mean()) if sl.any() else np.nan,
        gross_profit=float(gross_w), gross_loss=float(-gross_l),
        PF=float(gross_w / gross_l) if gross_l else np.inf,
        netR=float(v.sum()), ER=float(v.mean()))


def show(t, label):
    b = breakdown(t, label)
    v = t.netR.values
    tp, sl, to = (t.out == 1), (t.out == -1), (t.out == 0)
    print(f"\n{'='*72}\n{label}\n{'='*72}")
    print(f"  total trades      {b['n']}")
    print(f"  WIN  (target hit) {b['WIN']:>5}   {b['WIN']/b['n']*100:5.1f}%   "
          f"avg {b['avg_win']:+.3f}R   sum {v[tp].sum():+8.2f}R")
    print(f"  LOSS (stopped)    {b['LOSS']:>5}   {b['LOSS']/b['n']*100:5.1f}%   "
          f"avg {b['avg_loss']:+.3f}R   sum {v[sl].sum():+8.2f}R")
    if to.any():
        print(f"  TIMEOUT (24 h)    {b['TIMEOUT']:>5}   {b['TIMEOUT']/b['n']*100:5.1f}%   "
              f"avg {v[to].mean():+.3f}R   sum {v[to].sum():+8.2f}R")
        print(f"       of those:    {int((v[to]>0).sum())} closed green, "
              f"{int((v[to]<=0).sum())} closed red")
    print(f"\n  gross profit      {b['gross_profit']:+8.2f}R")
    print(f"  gross loss        {b['gross_loss']:+8.2f}R")
    print(f"  PROFIT FACTOR     {b['PF']:.4f}   = {b['gross_profit']:.2f} / "
          f"{abs(b['gross_loss']):.2f}")
    print(f"  net               {b['netR']:+8.2f}R      expectancy "
          f"{b['ER']:+.4f}R/trade")
    print(f"\n  breakeven win rate at this avg R:R = "
          f"{1/(1+abs(b['avg_win']/b['avg_loss'])) * 100:.1f}%   "
          f"actual {b['win_pct']*100:.1f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--exit", type=float, default=None, help="flat R exit")
    ap.add_argument("--cap", type=float, default=None, help="cap the pool at kR")
    ap.add_argument("--short", action="store_true", help="arm B, shorts only")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.all:
        rows = [breakdown(L.portfolio(shorts_only=a.short), "DYNAMIC pool (LOCKED)")]
        for k in (2.0, 2.5, 3.0, 3.5, 4.0, 5.0):
            rows.append(breakdown(L.portfolio(shorts_only=a.short, exit_rr=k),
                                  f"flat {k}R"))
        for k in (3.0, 4.0):
            rows.append(breakdown(L.portfolio(shorts_only=a.short, cap_rr=k),
                                  f"pool capped {k}R"))
        r = pd.DataFrame(rows)
        print(("ARM B - SHORTS ONLY" if a.short else "ARM A - BOTH SIDES")
              + "   (same 471 setups, only the exit moves)\n")
        print(r[["variant", "n", "WIN", "LOSS", "TIMEOUT", "win_pct", "avg_win",
                 "avg_loss", "gross_profit", "gross_loss", "PF", "netR"]]
              .to_string(index=False, float_format=f))
    else:
        kw = {}
        lbl = "DYNAMIC pool (LOCKED)"
        if a.exit is not None:
            kw["exit_rr"] = a.exit; lbl = f"flat {a.exit}R (gated)"
        elif a.cap is not None:
            kw["cap_rr"] = a.cap; lbl = f"pool capped at {a.cap}R"
        if a.short:
            lbl += "  [ARM B shorts only]"
        show(L.portfolio(shorts_only=a.short, **kw), lbl)
