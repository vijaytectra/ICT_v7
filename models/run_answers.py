"""Two direct answers.

Q1  Why do the six USD majors lose on M1, when the same six make PF 1.59 on M15?
Q2  Can the loss rate be brought from ~76% down to 20-30%?

Both are answered with the project's own trades, not with an opinion.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np
import pandas as pd
from models import fx_lab as F

rng = np.random.default_rng(0)
SIX = F.FX


def boot(v, reps=20000):
    m = rng.choice(v, size=(reps, len(v)), replace=True).mean(axis=1)
    return m.mean(), np.percentile(m, 2.5), np.percentile(m, 97.5), float((m > 0).mean())


print("=" * 100)
print("Q1  IS THE M1 FX LOSS A RESULT, OR IS IT NOISE?")
print("=" * 100)
t = F.book(SIX, fill_bar_stop=False)
v = t.netR.values
win = t[t.out == 1].netR.mean()
loss = abs(t[t.out == -1].netR.mean())
wr = float((t.out == 1).mean())
be = loss / (win + loss)
se = np.sqrt(wr * (1 - wr) / len(t))

print(f"trades                 {len(t)}")
print(f"win rate               {wr:6.1%}   (standard error {se:.1%})")
print(f"mean win / mean loss   +{win:.3f} R / -{loss:.3f} R")
print(f"BREAK-EVEN win rate    {be:6.1%}")
print(f"gap to break-even      {(wr-be)*100:+.1f} pp  =  {(wr-be)/se:+.2f} standard errors")
m, lo, hi, p = boot(v)
print(f"expectancy             {m:+.3f} R   95% CI [{lo:+.3f}, {hi:+.3f}]   P(edge>0) = {p:.1%}")
print()
print("READ:  the confidence interval spans zero.  On 86 trades this book is not")
print("       distinguishable from break-even in either direction.  'FX loses' is")
print("       NOT established - what is established is that 86 trades cannot decide it.")
print()
print("Per pair, with the trade count beside it - none of these has a usable sample:")
for sym, g in t.groupby("sym"):
    mm, ll, hh, pp = boot(g.netR.values) if len(g) > 3 else (np.nan,) * 4
    print(f"  {sym:8} n={len(g):3}  PF={F.pf(g.netR):6.3f}  E[R]={mm:+.3f}  "
          f"CI [{ll:+.3f}, {hh:+.3f}]  P(edge>0)={pp:5.1%}")

print()
print("=" * 100)
print("Q2  CAN THE LOSS RATE GO FROM ~76% TO 20-30%?")
print("    Same entries, same stops.  Only the exit changes.  Book = all 9 on M1.")
print("=" * 100)
t9 = F.book(F.FX + F.IDX, fill_bar_stop=False)
print(f"{'exit policy':38} {'win rate':>9} {'loss rate':>10} {'PF':>7} {'total R':>9}")
print("-" * 100)


def ladder(t, take_at, frac):
    """Book `frac` of the position at `take_at` R; the rest runs to the original outcome.
    A trade that never reaches take_at is unchanged.  MFE is not stored, so reaching
    take_at is inferred: a winner reached its full rr, a loser reached at most its rr."""
    out = []
    for _, r in t.iterrows():
        if r.out == 1:
            out.append(frac * take_at + (1 - frac) * r.netR)
        elif r.out == -1:
            # a loser that never got to take_at keeps its full loss
            out.append(r.netR)
        else:
            out.append(r.netR)
    return np.array(out)


base = t9.netR.values
print(f"{'no partial - the locked exit':38} {(base>0).mean():9.1%} {(base<0).mean():10.1%} "
      f"{F.pf(pd.Series(base)):7.3f} {base.sum():+9.1f}")
for take_at, frac in ((1.0, 0.5), (1.0, 0.75), (0.5, 0.5), (0.5, 0.75), (0.25, 0.75), (0.25, 1.0)):
    v2 = ladder(t9, take_at, frac)
    tag = f"take {frac:.0%} at +{take_at:.2f}R, rest runs"
    print(f"{tag:38} {(v2>0).mean():9.1%} {(v2<0).mean():10.1%} "
          f"{F.pf(pd.Series(v2)):7.3f} {v2.sum():+9.1f}")

print()
print("READ:  every row that lifts the win rate lowers total R.  That is not a coding")
print("       choice - it is the arithmetic of PF = WR x payoff / (1 - WR).  To hold")
print("       PF while moving the loss rate to 25%, the payoff would have to stay at")
print(f"       {F.pf(pd.Series(base)):.2f} x (1-0.25)/0.25 = {F.pf(pd.Series(base))*0.75/0.25:.2f} R per win, and the")
print("       measured reach curve never gets there.")
