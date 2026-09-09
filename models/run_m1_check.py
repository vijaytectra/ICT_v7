"""Resolve the E/F gap using M1 bid+ask, where the fill-bar blind spot is 60 seconds.

On M15 the difference between "check the stop on the fill bar" and "don't" is the
difference between PF 0.84 and PF 1.16 - a 15-minute window in which we cannot tell
whether the stop came before or after the limit filled.  On M1 that window is one
minute, so whichever answer M1 gives is close to the truth, and the size of the M1 gap
tells us how much of the M15 gap is genuine risk versus resolution artefact.
"""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
from models import fx_lab as F

print(f"{'book':22} {'fill-bar':10} | {'DEVn':>5} {'DEVPF':>6} {'DEV R':>8} | "
      f"{'VALn':>5} {'VALPF':>6} {'VAL R':>8}")
print("-" * 92)
for name, syms in (("FX (6 majors)", F.FX), ("Indices (3)", F.IDX), ("All 9", F.FX + F.IDX)):
    for fb in (False, True):
        t = F.book(syms, fill_bar_stop=fb)
        d, v = F.split(t)
        print(f"{name:22} {'ON' if fb else 'OFF':10} | "
              f"{len(d):5} {F.pf(d.netR):6.3f} {d.netR.sum():+8.1f} | "
              f"{len(v):5} {F.pf(v.netR):6.3f} {v.netR.sum():+8.1f}")
    print()

print("Long / short split on the 9, M1, fill-bar OFF (the generous case):")
t = F.book(F.FX + F.IDX, fill_bar_stop=False)
for side, lab in ((1, "longs "), (-1, "shorts")):
    v = t[t.side == side].netR
    print(f"  {lab} n={len(v):4} PF={F.pf(v):6.3f} R={v.sum():+8.1f}")
