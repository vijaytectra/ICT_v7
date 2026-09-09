"""Verify the LOCK itself, not the model.

A pinned test that can never fail is worthless.  This mutates every locked parameter
one at a time, in memory only (no file is touched), and confirms the pinned Arm A
result actually moves.  A parameter whose mutation leaves the numbers unchanged is not
really locked - it is either dead code or the pin does not cover it.

Also checks that models/asia_locked.py and ASIA_LOCKED.md agree, so the written spec
cannot drift away from the code that produced the numbers.

    python tests/verify_asia_lock.py
"""
import copy
import re
import subprocess
import sys
import pathlib

import numpy as np

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from tests.test_asia_locked import ARM_A

ROOT = pathlib.Path(r"C:\personal\ICT_v7")

# every locked knob, and a one-step perturbation of it
MUTATIONS = [
    ("DETECT", "n", 3), ("DETECT", "n", 7),
    ("DETECT", "max_gap", 30), ("DETECT", "max_gap", 60),
    ("DETECT", "disp_ratio", 0.4), ("DETECT", "disp_ratio", 0.7),
    ("DETECT", "pools", ("asia", "pdhl")),
    ("DETECT", "require_stl", True),
    ("DETECT", "require_bias", True),
    ("DETECT", "require_trend", True),
    ("DETECT", "kz", "LDN+NYAM"),
    ("EXECUTE", "entry", "edge"),
    ("EXECUTE", "stop_buf", 1.0),
    ("EXECUTE", "target", "fixed"),
    ("EXECUTE", "min_rr", 1.5), ("EXECUTE", "min_rr", 3.0),
    ("EXECUTE", "max_rr", 8.0), ("EXECUTE", "max_rr", 15.0),
    ("EXECUTE", "cri_max", 0.10), ("EXECUTE", "cri_max", 0.40),
    ("EXECUTE", "window_min", 240), ("EXECUTE", "window_min", 480),
    ("EXECUTE", "max_hold", 720),
]

# skip_dow is a trades() argument, not a DETECT/EXECUTE key, so it is mutated separately
DOW_MUTATIONS = [((), "no day filter"), ((0, 1), "skip Mon+Tue"), ((4,), "skip Fri")]

PINNED = ("n", "PF", "totR", "wr", "ER", "maxDD")


def measure():
    t = L.portfolio()
    s = L.summarise(t)
    return {k: s[k] for k in PINNED}


def measure_dow(val):
    s = L.summarise(L.portfolio(skip_dow=val))
    return {k: s[k] for k in PINNED}


def moved(a, b):
    return [k for k in PINNED
            if (a[k] != b[k] if isinstance(a[k], int) else abs(a[k] - b[k]) > 1e-4)]


def check_doc_matches_code():
    """Every locked value quoted in ASIA_LOCKED.md must equal the code."""
    md = (ROOT / "ASIA_LOCKED.md").read_text(encoding="utf-8")
    want = {
        "max_gap = 40": L.DETECT["max_gap"] == 40,
        "disp_ratio = 0.5": L.DETECT["disp_ratio"] == 0.5,
        "swing n = 5": L.DETECT["n"] == 5,
        'entry = "ce"': L.EXECUTE["entry"] == "ce",
        "window_min = 360": L.EXECUTE["window_min"] == 360,
        "stop_buf = 0": L.EXECUTE["stop_buf"] == 0.0,
        'target = "dol"': L.EXECUTE["target"] == "dol",
        "min_rr = 2.0": L.EXECUTE["min_rr"] == 2.0,
        "max_rr = 10.0": L.EXECUTE["max_rr"] == 10.0,
        "skip Monday": L.SKIP_DOW == (0,),
        "cri_max = 0.20": L.EXECUTE["cri_max"] == 0.20,
        "max_hold = 1440": L.EXECUTE["max_hold"] == 1440,
        "pools asia only": L.DETECT["pools"] == ("asia",),
        "gates off": not any((L.DETECT["require_stl"], L.DETECT["require_bias"],
                              L.DETECT["require_trend"])) and L.DETECT["kz"] is None,
    }
    fails = [k for k, ok in want.items() if not ok]
    # and the headline numbers quoted in the doc
    for pat, val in ((r"1\.2940", ARM_A["PF"]),
                     (r"\*\*395\*\*", ARM_A["n"]),
                     (r"\+87\.93", ARM_A["totR"])):
        if not re.search(pat, md):
            fails.append(f"ASIA_LOCKED.md no longer quotes {pat}")
    return fails


if __name__ == "__main__":
    print("=== 1. the lock test itself ===")
    r = subprocess.run([sys.executable, str(ROOT / "tests" / "test_asia_locked.py")],
                       capture_output=True, text=True, cwd=ROOT)
    print(f"  exit {r.returncode}   {'PASS' if r.returncode == 0 else 'FAIL'}")
    print("  " + r.stdout.strip().splitlines()[-1])

    print("\n=== 2. baseline matches the pin ===")
    base = measure()
    bad = moved(base, {k: ARM_A[k] for k in PINNED})
    print(f"  n={base['n']}  PF={base['PF']:.4f}  totR={base['totR']:+.3f}")
    print("  PASS" if not bad else f"  FAIL - drifted: {bad}")

    print("\n=== 3. does the lock actually BITE?  mutate each knob, in memory only ===")
    print(f"  {'parameter':<28}{'n':>6}{'PF':>9}{'totR':>10}   pinned fields moved")
    d0, e0 = copy.deepcopy(L.DETECT), copy.deepcopy(L.EXECUTE)
    dead = []
    for grp, key, val in MUTATIONS:
        tgt = L.DETECT if grp == "DETECT" else L.EXECUTE
        old = tgt[key]
        tgt[key] = val
        try:
            got = measure()
            mv = moved(base, got)
            lbl = f"{key}={val}"
            print(f"  {lbl:<28}{got['n']:>6}{got['PF']:>9.4f}{got['totR']:>+10.2f}"
                  f"   {len(mv)}/{len(PINNED)}" + ("" if mv else "   <-- NO EFFECT"))
            if not mv:
                dead.append(lbl)
        finally:
            tgt[key] = old
    L.DETECT.update(d0); L.EXECUTE.update(e0)

    print("\n  -- skip_dow (mutated separately: it is a trades() argument) --")
    for val, lbl in DOW_MUTATIONS:
        got = measure_dow(val)
        mv = moved(base, got)
        print(f"  {lbl:<28}{got['n']:>6}{got['PF']:>9.4f}{got['totR']:>+10.2f}"
              f"   {len(mv)}/{len(PINNED)}" + ("" if mv else "   <-- NO EFFECT"))
        if not mv:
            dead.append(lbl)

    print("\n=== 4. restored config still matches the pin ===")
    after = measure()
    bad2 = moved(after, {k: ARM_A[k] for k in PINNED})
    print("  PASS" if not bad2 else f"  FAIL - not restored: {bad2}")

    print("\n=== 5. ASIA_LOCKED.md agrees with the code ===")
    fd = check_doc_matches_code()
    print("  PASS" if not fd else "  FAIL:\n   - " + "\n   - ".join(fd))

    print()
    problems = (r.returncode != 0) or bad or bad2 or fd or dead
    if dead:
        print(f"WARNING: {len(dead)} parameter(s) had no effect on any pinned "
              f"number: {', '.join(dead)}")
        print("  -> either dead code, or the pin does not cover them.")
    print("LOCK VERIFIED" if not problems else "LOCK NOT VERIFIED")
    sys.exit(1 if problems else 0)
