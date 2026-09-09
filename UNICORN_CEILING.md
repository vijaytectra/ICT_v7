# Why the Unicorn cannot be made profitable — the measurement, not an opinion

Written 2026-09-06 after re-opening the question. The earlier "Unicorn: closed" note was
retracted first, because it quoted a cost-dependent number without recording the cost. This
document replaces it with a measurement that does not depend on any configuration choice.

## The test that settles it

For every signal the frozen detector produces, record how far price went in the trade's
favour **before the stop would have been hit**, in units of R. That reach curve is a
*ceiling*: no exit rule, target, trailing stop, partial or break-even can produce a hit rate
higher than the fraction of trades that actually reached the level. Compare it to the hit
rate the arithmetic demands: with cost `c` in R, a target `T` breaks even at `(1+c)/(T+1)`.

Index Unicorn, SETUP_INDEX config, three US indices, cost 1.5 index points:

| target | DEV 2015-2023 reached | needed | VAL 2024-2026 reached | needed |
|---|---|---|---|---|
| 1.0R | 49.3% | 55.8% | 50.7% | 52.9% |
| 1.5R | 36.9% | 44.6% | 40.1% | 42.3% |
| 2.0R | 29.2% | 37.2% | 34.4% | 35.3% |
| 3.0R | 18.4% | 27.9% | 21.9% | 26.5% |

**Every cell fails, in both periods.** 1,305 DEV trades and 424 VAL trades. There is no
target this population can pay for.

The same table for the Asian-range model, the one actually running, on its own 262 trades:

| target | reached | needed | |
|---|---|---|---|
| 0.50R | 66.8% | 72.8% | fail |
| 1.00R | 54.2% | 54.6% | fail |
| 1.50R | 44.7% | 43.7% | **pass** |
| 2.00R | 39.3% | 36.4% | **pass** |
| 3.00R | 32.1% | 27.3% | **pass** |
| 6.00R | 21.4% | 15.6% | **pass** |

That contrast is the whole project in one table. It also answers the standing request for a
high win rate: the working model clears the line only at 1.5R and above, and **fails at 1R
and below**. A high-win-rate version is not a design choice that was skipped, it is
arithmetically unavailable.

## What was tried before concluding

All on the frozen detector unless stated, selection on DEV 2015-2023 only, VAL 2024-2026 read
once, cost 1.5 index points.

| lever | source | best DEV PF |
|---|---|---|
| baseline, fixed 2R, swept-extreme stop | SETUP_INDEX | 0.877 |
| CRI gate, 8 thresholds 0.03-0.30 | brodenbeck v4 Screen 2 | 1.019 |
| fixed targets 1.0R to 6.0R | - | all negative E[R] |
| draw-on-liquidity target, 5 pools x 5 R:R gates | draw-on-liquidity.md | 1.678 (see below) |
| stop at the breaker / zone / MSS origin, x 3 targets x 5 CRI | the annotated cases | 0.861 |
| killzone LDN / NYAM / IDX / IDXALL / all hours | - | 1.503 (n=101) |
| premium-discount half, and the 62-79% OTE band | core ICT | 1.016 |
| pool = relative equal highs/lows instead of any swing | liquidity-sweep.md | 0.964 |
| nested-FVG strictness (gap inside the breaker body) | SrsBlack 08-breaker-blocks | 1.024 |

Two arms looked like results and were killed by the checks the project already requires:

- **DOL target, min R:R 2.0 — DEV PF 1.238, VAL 1.693.** Per year it is positive in 4 of 9,
  and the entire DEV profit is +32.8R from **six trades in 2023**. Leave-one-out fails in
  both directions: without USATECH DEV is 0.912, without USA30 VAL is 0.968. Bootstrap
  P(edge>0) on DEV is 72.6% with a 95% CI of [-0.318, +0.921]. Rejected.
- **Per-instrument splits invert between periods.** On the DOL arm DEV is carried by USATECH
  (1.98) which is the worst on VAL (0.93), while VAL is carried by USA30 (3.01) which is the
  worst on DEV (0.87). Anti-correlation, not an edge.

## The one true thing about the Unicorn

At **spread-only cost** it is mildly positive across twelve years: DEV PF 1.080 / +63.5R,
VAL 1.218 / +54.3R. Breakeven is about **0.5 index points** of cost beyond the spread. So the
honest statement is not "no edge ever" - it is that the edge is smaller than the cost of
trading it, and the reach curve says why: the entry never gets far enough, often enough.
