"""Re-run the whole broker dump with a real ask, a real cost and the documented order life."""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models import screen_fixed as S, portfolio_locked as P

pd.set_option("display.width", 200)

print("Screening the broker dump with the three defects corrected ...")
t = S.screen()
print(f"\ninstruments with trades: {t.sym.nunique()}   total trades: {len(t)}\n")

print("=" * 100)
print("POOLED, BY GROUP")
print("=" * 100)
uni = set(P.UNIVERSE)
S.summarise(t, "everything dumped")
S.summarise(t[t.sym.isin(uni)], "locked universe (33)")
S.summarise(t[t.sym.isin(P.MAJORS)], "7 USD majors")
S.summarise(t[t.sym.isin(P.CROSSES)], "21 major crosses")
S.summarise(t[t.sym.isin(P.INDICES)], "5 index CFDs")

print()
print("=" * 100)
print("PER INSTRUMENT - locked universe, sorted by total R")
print("=" * 100)
ps = S.per_symbol(t[t.sym.isin(uni)])
print(ps.to_string(index=False, float_format=lambda x: f"{x:7.3f}"))

pos_both = ps[(ps.PF_dev > 1.0) & (ps.PF_val > 1.0)]
print(f"\ninstruments positive in BOTH halves: {len(pos_both)} of {len(ps)}")
print("  " + ", ".join(pos_both.sym.tolist()))

t.to_csv(r"C:\personal\ICT_v7\reports\screen_fixed_trades.csv", index=False)
ps.to_csv(r"C:\personal\ICT_v7\reports\screen_fixed_per_symbol.csv", index=False)
print("\nwritten: reports/screen_fixed_trades.csv, reports/screen_fixed_per_symbol.csv")
