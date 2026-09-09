"""Is 50%-at-+0.5R-plus-breakeven a peak on a cliff, or the middle of a smooth region?

The project's own standard (DOL_REACHABILITY.md): a parameter is only trustworthy when
its neighbours behave the same way.  A single cell that works surrounded by cells that
do not is a fluke that survived a search.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models import fx_lab as F
from models.run_ladder import apply_ladder

for label, syms in (("3 INDICES", F.IDX), ("ALL 9", F.FX + F.IDX)):
    t = F.book(syms, fill_bar_stop=False).sort_values("t").reset_index(drop=True)
    dm = (t.t <= t.t.quantile(0.6)).values
    print("=" * 108)
    print(f"{label}   -   VAL profit factor for each (take-at, fraction), break-even on the remainder")
    print("=" * 108)
    fracs = (0.25, 0.33, 0.5, 0.67, 0.75)
    print(f"{'take at':>9} | " + " ".join(f"{f:>13.0%}" for f in fracs))
    print("-" * 108)
    for take in (0.25, 0.4, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5):
        cells = []
        for fr in fracs:
            v = apply_ladder(t, take, fr, breakeven=True)
            vv = v[~dm]
            dv = v[dm]
            cells.append(f"{F.pf(pd.Series(dv)):5.2f}/{F.pf(pd.Series(vv)):5.2f}")
        print(f"{take:9.2f} | " + " ".join(f"{c:>13}" for c in cells))
    print("   (each cell is DEV PF / VAL PF; the locked no-partial baseline is "
          f"{F.pf(pd.Series(t.netR.values[dm])):.2f}/{F.pf(pd.Series(t.netR.values[~dm])):.2f})")
    print()
