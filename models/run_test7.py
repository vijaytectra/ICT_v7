import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L
from models.random_control import prep, control
pd.set_option("display.width", 200); f = lambda x: f"{x:.3f}"

REPS = 200
for arm, shorts in (("ARM A", False), ("ARM B", True)):
    real = L.portfolio(shorts_only=shorts)
    print("=" * 104)
    print(f"TEST 7 — RANDOM ENTRY CONTROL, {arm}   ({REPS} replications)")
    print(f"  real: n={len(real)}  PF={L.pf(real.netR.values):.4f}  "
          f"E[R]={real.netR.mean():+.4f}  totR={real.netR.sum():+.1f}")
    print("=" * 104)
    rows = []
    for mode, desc in (("C1", "random TIME, real side"),
                       ("C2", "real time, random SIDE"),
                       ("C3", "random time AND side")):
        allpf, aller = [], []
        for sym in L.ALL:
            sub = real[real.sym == sym]
            if len(sub) < 5:
                continue
            df = prep(sym)
            pf, er, n = control(sub, sym, df, mode, reps=REPS, seed=hash(sym) % 10000)
            allpf.append(pf * len(sub)); aller.append(er * len(sub))
        w = sum(len(real[real.sym == s]) for s in L.ALL if len(real[real.sym == s]) >= 5)
        pf = np.nansum(allpf, axis=0) / w
        er = np.nansum(aller, axis=0) / w
        rows.append(dict(control=f"{mode}  {desc}",
                         PF_mean=np.nanmean(pf), PF_median=np.nanmedian(pf),
                         PF_p05=np.nanpercentile(pf, 5), PF_p95=np.nanpercentile(pf, 95),
                         PF_max=np.nanmax(pf),
                         ER_mean=np.nanmean(er),
                         beat_real=float(np.nanmean(pf >= L.pf(real.netR.values)))))
    r = pd.DataFrame(rows)
    r.to_csv(rf"C:\personal\ICT_v7\reports\test7_{arm.replace(' ','')}.csv", index=False)
    print(r.to_string(index=False, float_format=f))
    print(f"\n  beat_real = fraction of the {REPS} random books whose PF matched or beat "
          f"the real {L.pf(real.netR.values):.3f}\n")
