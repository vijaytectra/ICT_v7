"""Sweep the untested axes on FX with the corrected engine.  Prints DEV and VAL together."""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
from models import fx_lab as F

print("=" * 96)
print("CONTROL - does the corrected engine reproduce the shape of the locked model?")
print("=" * 96)
for name, syms in (("FX (6 majors)", F.FX), ("Indices (3)", F.IDX), ("All 9", F.FX + F.IDX)):
    t = F.book(syms)
    print(F.line(name + "  entry=0.5 (locked)", t))

print()
print("=" * 96)
print("AXIS 1 - ENTRY POSITION INSIDE THE FVG   (PART 5 item 6: never tested)")
print("  0.0 = near edge (shallow, fills often)   0.5 = ce, the locked value   1.0 = far edge")
print("=" * 96)
for f in (0.0, 0.25, 0.5, 0.75, 1.0):
    print(F.line(f"FX  entry_frac={f:.2f}", F.book(F.FX, entry_frac=f)))
print()
for f in (0.0, 0.25, 0.5, 0.75, 1.0):
    print(F.line(f"IDX entry_frac={f:.2f}", F.book(F.IDX, entry_frac=f)))

print()
print("=" * 96)
print("AXIS 2 - PATH FILTER: HEADROOM   target distance / distance to nearest opposing pool")
print("  (PART 5 item 5: 'the one class nobody has built')")
print("=" * 96)
for hz in (0.0, 0.5, 1.0, 1.5, 2.0):
    print(F.line(f"FX  min_hz={hz:.1f}", F.book(F.FX, min_hz=hz)))

print()
print("=" * 96)
print("AXIS 3 - PATH FILTER: RECENCY   bars since the target was last crossed on a close")
print("=" * 96)
for r in (0, 96, 48, 24, 12):
    tag = "off" if r == 0 else f"<= {r} bars"
    print(F.line(f"FX  recency {tag}", F.book(F.FX, max_recency=r)))

print()
print("=" * 96)
print("AXIS 4 - R:R GATE on FX only")
print("=" * 96)
for lo in (1.5, 2.0, 2.5, 3.0):
    print(F.line(f"FX  min_rr={lo}", F.book(F.FX, min_rr=lo)))
