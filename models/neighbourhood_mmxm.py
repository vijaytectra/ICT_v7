"""Neighbourhood test on the one config that survived both halves of the pooled
indices, plus the FX transfer test (H5).

A real edge is a REGION of parameter space, not a point.  v4's Unicorn passed this:
nudging each knob one step left 16 of 17 variants profitable.  Anything that only
works at one exact coordinate is a lottery ticket drawn from 162 tries.
"""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import mmxm_bt, mmxm_lab
from models.run_mmxm import BASE

REP = pathlib.Path(r"C:\personal\ICT_v7\reports")

DET = dict(BASE); DET["require_discount"] = False
EXE = dict(entry="mt", target="erl", min_rr=1.5, kz="LDN")

VARIANTS = [
    ("BASE                      ", DET, EXE, "15min", "4h"),
    ("entry = zone edge         ", DET, {**EXE, "entry": "edge"}, "15min", "4h"),
    ("entry = CISD level        ", DET, {**EXE, "entry": "cisd"}, "15min", "4h"),
    ("killzone = NY AM index    ", DET, {**EXE, "kz": "IDX"}, "15min", "4h"),
    ("killzone = none           ", DET, {**EXE, "kz": "ALL"}, "15min", "4h"),
    ("min R:R 1.0               ", DET, {**EXE, "min_rr": 1.0}, "15min", "4h"),
    ("min R:R 2.0               ", DET, {**EXE, "min_rr": 2.0}, "15min", "4h"),
    ("target fixed 2R           ", DET, {"entry": "mt", "target": "fixed", "rr": 2.0,
                                         "kz": "LDN"}, "15min", "4h"),
    ("target fixed 3R           ", DET, {"entry": "mt", "target": "fixed", "rr": 3.0,
                                         "kz": "LDN"}, "15min", "4h"),
    ("discount gate ON          ", {**DET, "require_discount": True}, EXE, "15min", "4h"),
    ("swing n = 3               ", {**DET, "n": 3}, EXE, "15min", "4h"),
    ("swing n = 7               ", {**DET, "n": 7}, EXE, "15min", "4h"),
    ("window 25 bars            ", {**DET, "max_gap": 25}, EXE, "15min", "4h"),
    ("window 60 bars            ", {**DET, "max_gap": 60}, EXE, "15min", "4h"),
    ("pool = equal highs/lows   ", {**DET, "sweep_pool": "equal"}, EXE, "15min", "4h"),
    ("liquidity off bodies      ", {**DET, "body_liquidity": True}, EXE, "15min", "4h"),
    ("structure TF 5 min        ", DET, EXE, "5min", "4h"),
    ("structure TF 30 min       ", DET, EXE, "30min", "4h"),
    ("HTF = 1 hour              ", DET, EXE, "15min", "1h"),
    ("HTF = daily               ", DET, EXE, "15min", "1D"),
]


def pf(t):
    if t is None or len(t) == 0:
        return np.nan
    g = t.netR[t.netR > 0].sum(); b = -t.netR[t.netR < 0].sum()
    return float(g / b) if b > 0 else np.inf


if __name__ == "__main__":
    print("=== NEIGHBOURHOOD, pooled US100 + US500 + US30, full period ===\n")
    rows = []
    for name, d, e, tf, htf in VARIANTS:
        t = mmxm_lab.pooled(mmxm_lab.INDICES, d, e, tf=tf, htf=htf)
        i_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, e, tf=tf, htf=htf, period="IS")
        o_t = mmxm_lab.pooled(mmxm_lab.INDICES, d, e, tf=tf, htf=htf, period="OOS")
        rows.append(dict(variant=name, n=len(t), PF=pf(t),
                         totR=float(t.netR.sum()) if len(t) else np.nan,
                         is_PF=pf(i_t), oos_PF=pf(o_t)))
    r = pd.DataFrame(rows)
    r.to_csv(REP / "mmxm_neighbourhood.csv", index=False)
    print(r.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    ok = r.dropna(subset=["PF"])
    print(f"\nprofitable variants: {(ok.PF > 1.0).sum()} of {len(ok)}")

    print("\n=== the BASE config, per instrument ===\n")
    rows = []
    for s in mmxm_lab.INDICES + mmxm_lab.FX:
        t = mmxm_lab.evaluate(s, DET, EXE)
        st = mmxm_bt.stats(t, s)
        if st:
            st["P_edge"], ci = mmxm_bt.bootstrap(t)
            st["ci_lo"], st["ci_hi"] = ci
            rows.append(st)
    p = pd.DataFrame(rows)
    print(p[["arm", "n", "wr", "ER", "PF", "totR", "maxDD", "P_edge", "ci_lo", "ci_hi"]]
          .to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    print("\n=== H5, the transfer test: six FX majors, same frozen config ===\n")
    fx = mmxm_lab.pooled(mmxm_lab.FX, DET, EXE)
    idx = mmxm_lab.pooled(mmxm_lab.INDICES, DET, EXE)
    for nm, t in (("US indices", idx), ("six FX majors", fx)):
        st = mmxm_bt.stats(t, nm)
        if st:
            pe, ci = mmxm_bt.bootstrap(t)
            print(f"  {nm:15s} n={st['n']:4d}  WR {st['wr']:.3f}  PF {st['PF']:.3f}  "
                  f"totR {st['totR']:+7.1f}  P(edge>0) {pe:.3f}")
