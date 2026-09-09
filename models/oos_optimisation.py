"""Conservative M1 bid/ask execution primitives for research-only replays.

This module deliberately contains no signal generation.  It protects every future
setup test from the two easiest sources of inflated results: using the wrong side of
the quote and assuming a favourable order when one M1 bar touches both barriers.
"""

from __future__ import annotations

from typing import Literal

import pandas as pd


Status = Literal["unfilled", "expired", "stop", "target"]


def evaluate_trade_path(
    bars: pd.DataFrame,
    *,
    side: int,
    entry: float,
    stop: float,
    target: float,
) -> dict[str, object]:
    """Replay a limit order against bid/ask M1 bars.

    A buy order enters only when ask trades at or below its limit and exits on bid;
    a sell order enters only when bid trades at or above its limit and exits on ask.
    Intrabar chronology is unavailable in M1 OHLC, so a bar that reaches both stop
    and target always scores the stop first.
    """
    if side not in (1, -1):
        raise ValueError("side must be 1 (long) or -1 (short)")
    if bars.empty:
        return {"status": "unfilled", "fill_time": None, "exit_time": None}

    required = {"h_b", "l_b", "h_a", "l_a"}
    missing = required.difference(bars.columns)
    if missing:
        raise ValueError(f"bars missing required quote columns: {sorted(missing)}")

    filled = False
    fill_time = None
    for timestamp, bar in bars.iterrows():
        if not filled:
            fillable = bar.l_a <= entry if side == 1 else bar.h_b >= entry
            if not fillable:
                continue
            filled = True
            fill_time = timestamp

        if side == 1:
            hit_stop = bar.l_b <= stop
            hit_target = bar.h_b >= target
        else:
            hit_stop = bar.h_a >= stop
            hit_target = bar.l_a <= target

        if hit_stop:
            return {"status": "stop", "fill_time": fill_time, "exit_time": timestamp}
        if hit_target:
            return {"status": "target", "fill_time": fill_time, "exit_time": timestamp}

    status: Status = "expired" if filled else "unfilled"
    return {"status": status, "fill_time": fill_time, "exit_time": None}
