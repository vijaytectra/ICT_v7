"""SMT divergence filter for the Asian-range model.

The idea, straight from the sources: two correlated instruments should sweep the same
side together. When one takes out its Asian low and the PARTNER does not, the low is not
confirmed by the market as a whole - the sweep is a failure, and the reversal the model is
betting on is the more likely outcome. When both sweep, the move is real and the reversal
is less likely.

This is a pure post-filter on already-emitted signals. It reads only the partner's bars up
to and including the raid bar, so it is causal. It has never been tested in this project.
"""
import numpy as np
import pandas as pd


def partner_state(partner_bars, partner_asia, t_raid, side):
    """Did the partner also sweep, at or before the raid bar of the primary?

    side +1 is a sell-side raid (a LOW was taken, we go long); the partner confirms by
    also trading below its own Asian low on that bar. side -1 mirrors.
    Returns (swept, have_levels).
    """
    i = partner_bars.index.searchsorted(t_raid, "right") - 1
    if i < 0: return None, False
    row = partner_bars.iloc[i]
    day = partner_bars.index[i].normalize()
    if day not in partner_asia.index: return None, False
    ah, al = partner_asia.loc[day, "ah"], partner_asia.loc[day, "al"]
    if partner_bars.index[i].hour < 9: return None, False
    if side == 1:
        if not np.isfinite(al): return None, False
        return bool(row.l_b < al), True
    else:
        if not np.isfinite(ah): return None, False
        return bool(row.h_b > ah), True


def tag(rows, bars_map, asia_map, pairs):
    """Add an `smt` column to a list of path records.

      'diverged'  the partner did NOT sweep with us   -> the sweep is unconfirmed
      'confirmed' the partner swept too
      'unknown'   no partner data for that bar
    """
    out = []
    for r in rows:
        p = pairs.get(r["sym"])
        if p is None or p not in bars_map:
            r = dict(r); r["smt"] = "unknown"; out.append(r); continue
        swept, ok = partner_state(bars_map[p], asia_map[p], r["t_raid"], r["side"])
        r = dict(r)
        r["smt"] = "unknown" if not ok else ("confirmed" if swept else "diverged")
        out.append(r)
    return out
