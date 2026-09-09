"""Execute the frozen Stage A / Stage B contract.  Writes every trade to disk so the
tables can be re-derived without re-running, and so a later stage cannot quietly change
an earlier one."""
import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\personal\ICT_v7")
from models import asia_locked as L
from models import fvg_target_lab as F

OUT = pathlib.Path(r"C:\personal\ICT_v7\reports\stage_ab")
OUT.mkdir(parents=True, exist_ok=True)


def cell(variant, unswept):
    tag = f"{variant}{'_UNSWEPT' if unswept else ''}"
    fd = OUT / f"{tag}__DEV.csv"
    fv = OUT / f"{tag}__VAL.csv"
    if fd.exists() and fv.exists():
        return (pd.read_csv(fd, parse_dates=["t"]),
                pd.read_csv(fv, parse_dates=["t"]))
    d = F.run(L.INDICES, True, variant, unswept)
    v = F.run(L.ALL, False, variant, unswept)
    d.to_csv(fd, index=False)
    v.to_csv(fv, index=False)
    return d, v


def rows_for(tag, d, v):
    out = []
    for lab, syms, hist, t in (("DEV", L.INDICES, True, d),
                               ("VAL-IDX", L.INDICES, False,
                                v[v.sym.isin(L.INDICES)]),
                               ("VAL-FX", L.FX, False, v[v.sym.isin(L.FX)]),
                               ("VAL", L.ALL, False, v)):
        m = F.metrics(t.reset_index(drop=True), syms, hist)
        if m:
            out.append(dict(variant=tag, slice=lab, **m))
    return out


if __name__ == "__main__":
    if not F.control():
        sys.exit("control failed - refusing to report variants")
    plan = [(x, False) for x in F.VARIANTS] + [("FIRST", True)]
    rows, store = [], {}
    for var, un in plan:
        tag = f"{var}{'_UNSWEPT' if un else ''}"
        d, v = cell(var, un)
        store[tag] = (d, v)
        rows += rows_for(tag, d, v)
        print(f"done {tag}: DEV {len(d)}  VAL {len(v)}", flush=True)
    r = pd.DataFrame(rows)
    r.to_csv(OUT / "summary.csv", index=False)
    print("\nwritten", OUT / "summary.csv")
