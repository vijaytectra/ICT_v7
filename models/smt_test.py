"""Validate the SMT divergence filter properly before believing it."""
import sys
sys.path.insert(0, r"C:\personal\ICT_v7")
import numpy as np, pandas as pd
from models import asia_locked as L, asia_dev, ict_bt, ict_system, smt

DEFAULT = {'USATECH':'USA30','USA30':'USATECH','USA500':'USA30',
           'EURUSD':'GBPUSD','GBPUSD':'EURUSD','AUDUSD':'EURUSD',
           'USDCHF':'USDCAD','USDCAD':'USDCHF','USDJPY':'USDCHF'}


def pf(v):
    v = np.asarray(v); g = v[v > 0].sum(); b = -v[v < 0].sum()
    return g / b if b > 0 else np.inf


def run(syms, hist, pairs=DEFAULT, gate=2.0):
    bars_map, asia_map = {}, {}
    for s in set(syms) | set(pairs.values()):
        try:
            df, b, _ = asia_dev.prep(s, hist)
            bars_map[s] = b; asia_map[s] = ict_system.session_pools(df)
        except Exception:
            pass
    out = []
    for s in syms:
        df, b, sigs = asia_dev.prep(s, hist)
        recs = [dict(sym=s, side=g['side'], t_raid=b.index[g['sweep_bar']], bar=g['bar'])
                for g in sigs]
        lab = {(r['bar'], r['side']): r['smt'] for r in smt.tag(recs, bars_map, asia_map, pairs)}
        t = ict_bt.run(df, sigs, b.index, L.UNIT[s], pd.Timedelta('15min'),
                       **{**L.EXECUTE, 'cost': 0.4 * L.median_spread(s, hist) * L.UNIT[s],
                          'min_rr': gate, 'extra': ['pool']})
        if not len(t): continue
        t = t.assign(sym=s)
        t['smt'] = [lab.get((int(bb), int(sd)), 'unknown')
                    for bb, sd in zip(t['_bar'], t['side'])]
        out.append(t)
    r = pd.concat(out)
    if L.SKIP_DOW: r = r[~r.t.dt.dayofweek.isin(L.SKIP_DOW)]
    return r.reset_index(drop=True)
