"""The four survivors, examined for mechanism and tested in combination.

Fourteen filters were tested; four improved both periods.  Under a null where each
filter is a coin flip on the holdout you would expect about seven, so 4/14 is NOT by
itself evidence.  What separates a rule from a coincidence is a mechanism that was
written down in the source material BEFORE the data was looked at.

  skip Monday        STRONG.  Weekly PO3: Monday is the WEEKLY accumulation phase; the
                     weekly manipulation is Tuesday and the weekly extreme forms Tue/Wed
                     (SrsBlack weekly-range-profiles.md, monday-wednesday-range.md,
                     market-maker-manipulation-template.md: "hold into Thursday's New
                     York session").  Running a DAILY manipulation model on the day that
                     is itself the weekly accumulation is doctrinally backwards.  Also
                     mechanical: Monday's Asian range follows a weekend gap.

  raid depth < 0.11  STRONG.  SrsBlack market-maker-trap.md: "on the breakout, check
                     what price actually reached - it only traded just above this old
                     high - a stop run, not an expansion."  A shallow poke is a stop
                     run; a deep break is a real expansion and there is nothing to fade.

  entry_pos < 0.15   MODERATE.  The FVG's midpoint must sit near the raided bound.  If
                     the entry is deep inside the range the reversal was slow, and the
                     stop at the raid extreme is now a stretched one.  Same family as
                     brodenbeck v4 Screen 2 (already in the model as cri_max) and the
                     v2 25-pip risk cap.

  skip rr 4-5        NONE.  A hole in the middle of the R:R distribution with no story.
                     Rejected on that basis, whatever the number says.
"""
import itertools
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import loss_analysis as A

f = lambda x: f"{x:.3f}"

F = {
    "MON": ("skip Monday", lambda d: d.dow != 0),
    "DEPTH": ("raid depth < 0.11", lambda d: d.depth < 0.106),
    "POS": ("entry_pos < 0.15", lambda d: d.entry_pos < 0.15),
}


def stat(d, label):
    if d is None or len(d) < 15:
        return None
    v = d.netR.values
    gl = -v[v < 0].sum()
    eq = v.cumsum()
    s = mx = 0
    for x in v:
        s = s + 1 if x <= 0 else 0
        mx = max(mx, s)
    p, ci = L.bootstrap(v)
    return dict(combo=label, n=len(v), WR=float((d.out == 1).mean()),
                ER=float(v.mean()), PF=float(v[v > 0].sum() / gl) if gl else np.inf,
                totR=float(v.sum()),
                maxDD=float((eq - np.maximum.accumulate(eq)).min()),
                streak=mx, P_edge=p, ci_lo=ci[0])


def apply(d, keys):
    m = np.ones(len(d), bool)
    for k in keys:
        m &= F[k][1](d).values
    return d[m]


if __name__ == "__main__":
    live, hold = A.live(), A.hold()

    print("=" * 118)
    print("OVERLAP — are the three filters measuring the same thing?")
    print("=" * 118)
    m = pd.DataFrame({k: F[k][1](live).values for k in F})
    print(m.astype(int).corr().to_string(float_format=f))

    print("\n" + "=" * 118)
    print("EVERY COMBINATION, BOTH PERIODS")
    print("=" * 118)
    rows = []
    for r_ in range(0, len(F) + 1):
        for keys in itertools.combinations(F, r_):
            lab = "+".join(keys) if keys else "BASE"
            sl = stat(apply(live, keys), lab)
            sh = stat(apply(hold, keys), lab)
            if sl is None or sh is None:
                continue
            rows.append(dict(combo=lab,
                             live_n=sl["n"], live_WR=sl["WR"], live_PF=sl["PF"],
                             live_totR=sl["totR"], live_DD=sl["maxDD"],
                             live_streak=sl["streak"], live_Pedge=sl["P_edge"],
                             hold_n=sh["n"], hold_PF=sh["PF"], hold_totR=sh["totR"],
                             hold_Pedge=sh["P_edge"]))
    r = pd.DataFrame(rows)
    r.to_csv(r"C:\personal\ICT_v7\reports\loss_combos.csv", index=False)
    print(r.to_string(index=False, float_format=f))

    print("\n" + "=" * 118)
    print("ARM B (shorts only) — the same combinations")
    print("=" * 118)
    lb, hb = live[live.side == -1], hold[hold.side == -1]
    rows = []
    for r_ in range(0, len(F) + 1):
        for keys in itertools.combinations(F, r_):
            lab = "+".join(keys) if keys else "BASE"
            sl = stat(apply(lb, keys), lab)
            sh = stat(apply(hb, keys), lab)
            if sl is None or sh is None:
                continue
            rows.append(dict(combo=lab, live_n=sl["n"], live_WR=sl["WR"],
                             live_PF=sl["PF"], live_totR=sl["totR"],
                             live_DD=sl["maxDD"], live_Pedge=sl["P_edge"],
                             hold_n=sh["n"], hold_PF=sh["PF"], hold_totR=sh["totR"],
                             hold_Pedge=sh["P_edge"]))
    print(pd.DataFrame(rows).to_string(index=False, float_format=f))

    print("\n" + "=" * 118)
    print("MONDAY, looked at directly")
    print("=" * 118)
    for nm, d in (("2024-2026", live), ("2015-2023 holdout", hold)):
        g = d.groupby(d.dow).agg(n=("netR", "size"), WR=("out", lambda v: (v == 1).mean()),
                                 ER=("netR", "mean"), totR=("netR", "sum"),
                                 PF=("netR", lambda v: L.pf(v.values)))
        g.index = ["Mon", "Tue", "Wed", "Thu", "Fri"][:len(g)]
        print(f"\n  {nm}")
        print(g.to_string(float_format=f))
