# RETRACTED - there is no setup

The Unicorn model was rebuilt from scratch (`models/unicorn_v3.py`) after a detector bug
invalidated everything below, and after a full re-read of all three reference repositories.

**216 configurations tested on six FX majors. Zero have a profit factor above 1.0.**
Best 0.900, median 0.806. Grid: strict/loose sweep x swing 3/5 x displacement 0.5/0.7 x
entry edge/CE/mean-threshold x target 2R/3R/4R x London / London+NY / all hours.

Applying the doctrinally correct sweep definition ("sweep wicks; BOS closes") made results
worse, not better: PF 0.73 against 0.82 for the loose reading.

Everything below this line is the retracted v2 document, kept only as a record of method.

---

# RETRACTED - do not trade this

Every figure below was produced by a detector with a sweep-state bug that emitted 190-490
signals per pair instead of ~2,500. Corrected, on six FX majors: n=1,592, PF **0.83**,
**-204.7R**, P(edge>0) = **0.0%**. The document is kept only as a record of the method.

---

# The Setup - ICT Unicorn, London Killzone

Rules mined from three sources (OpenMobius KB, brodenbeck1/ict_trading,
SrsBlack/ict-knowledge-library), consolidated in `models/SPEC.md`, each one measured
rather than assumed. Selected in-sample (2024-01 to 2025-06), confirmed once on
reserved data (2025-07 to 2026-09). Rule IDs below refer to `models/SPEC.md`.

## Entry rules (bullish; bearish mirrors exactly)

**Structure and signals on M5. Execution on M1.**

1. **Swing points** - a swing low needs 3 bars either side. It is *confirmed 3 bars
   later* and may not be used before that bar. (Causality; prefix-invariance tested.)
2. **R1 Sweep** - price trades **below** the last confirmed swing low. Record the sweep
   low `SL_px`, and freeze the last confirmed swing **high** `SH_ref` at this moment.
3. **R3 Window** - the next step must happen within **60 M5 bars** of the sweep, else reset.
4. **R2+R4 MSS with displacement** - an M5 candle **closes above `SH_ref`**, is an
   up-close candle, and has **body / (high - low) >= 0.5**.
5. **R7 Breaker** - the last consecutive run of **down-close** candles between the sweep
   and the MSS candle. Zone = `[min low, max high]` of that run, wicks included.
6. **R6 FVG** - scan only bars inside the sweep-to-MSS leg for a 3-candle gap
   (`low[k] > high[k-2]`). Zone = `[high[k-2], low[k]]`. An FVG outside the leg is invalid.
7. **R8 Overlap** - `entry_zone = intersect(breaker, FVG)`, must be **non-empty**.
   Touching edges do not qualify. First qualifying FVG wins.
8. **R12 Killzone** - the fill must occur between **09:00 and 12:00 EET** (London).
   Signals outside the window are discarded, not deferred.
9. **Entry** - resting **buy limit at `zone_high`**, valid 240 minutes, then cancel.
   No chasing.
10. **R15 Stop** - `SL_px`, the swept extreme. *Not* the zone edge - see below.
11. **R17 Risk cap** - if `entry - stop` exceeds **25 pips**, skip the setup. A stop that
    wide means the sweep sat abnormally far from the entry and the structure is stretched.
    This is the only cohort in the whole sample with negative expectancy.
12. **R16 Target** - **2R** or **4R**, fixed. Both validated; choose per the table below.
13. One position at a time. No new entry until the open one resolves.

## Measured - 3 pairs, 2024-01 to 2026-09, 0.7 pip commission on top of real spread

All figures below come from one engine (`models/bt3.py`) so they are directly comparable.
Win rate is target-hit / all trades.

With the 25-pip risk cap (R17). Figures without the cap are in brackets.

| | 2R | 4R |
|---|---|---|
| trades | 135 (4.2/mo) [149] | 133 [147] |
| target hit / stopped / timeout | 65 / 70 / 0 | 40 / 93 / 0 |
| win rate | **48.15%** [44.97%] | **30.1%** [33.3%] |
| breakeven win rate | 33.3% | 20.0% |
| expectancy | +0.328 R [+0.272] | **+0.483 R** [+0.411] |
| profit factor | **1.57** [1.47] | **1.66** [1.56] |
| total | +44.3 R [+40.5] | **+64.3 R** [+60.4] |
| max drawdown | **-9.8 R** [-10.8] | -16.6 R [-17.7] |
| R earned per R of drawdown | **4.53** [3.75] | 3.87 [3.41] |
| longest losing streak | **8** | 10 |
| median hold | **37 min** [45] | 68 min |
| median stop | 7.5 pips [8.2] | 7.5 pips |
| bootstrap P(edge > 0) | **99.4%** [98.6%] | 99.3% |
| IS PF -> OOS PF | **1.61 -> 1.51** [1.52 -> 1.39] | 1.72 -> 1.55 |
| bootstrap 95% CI on E[R] | [+0.080, +0.581] | [+0.115, +0.868] |

Per pair - all six positive:

| pair | 2R n | 2R WR | 2R PF | 2R totR |
|---|---|---|---|---|
| USDJPY | 30 | 0.600 | **2.60** | +21.1 |
| EURUSD | 38 | 0.500 | 1.65 | +14.0 |
| GBPUSD | 67 | 0.418 | 1.21 | +9.2 |

Cost robustness:

| commission | 0.0p | 0.7p | 1.0p | 1.5p | 2.0p | 3.0p |
|---|---|---|---|---|---|---|
| PF at 2R (capped) | 1.86 | **1.57** | 1.46 | 1.30 | 1.16 | 0.93 |

Expected return at 2R: risk 1%/trade -> about **+1.4%/month**, worst modelled drawdown -9.8%.
At 4R: about +2.0%/month, worst modelled drawdown -16.6%.

### Where the losses were

| stop size | n | WR | E[R] | total R |
|---|---|---|---|---|
| < 5 pips | 30 | 0.533 | +0.356 | +10.7 |
| 5-8 pips | 44 | 0.477 | +0.322 | +14.2 |
| 8-12 pips | 30 | 0.433 | +0.229 | +6.9 |
| 12-20 pips | 29 | 0.483 | +0.400 | +11.6 |
| **> 20 pips** | **16** | **0.375** | **-0.178** | **-2.9** |

One cohort out of five carries all the structural loss. Cutting it raises win rate,
profit factor and total return at once, and *lowers* drawdown - the only change tested in
this project that improved every metric simultaneously. Grounded in brodenbeck's v4
Screen 2 (cost / structural risk), which sets a floor on stop size; this sets a ceiling.

## Why the stop is wide, against the sources' own advice

Both knowledge bases list "stop at the far swing instead of tight to the overlap zone"
as a *common mistake*. Measured on this data it is the opposite:

| stop rule | median risk | win rate | E[R] |
|---|---|---|---|
| swept extreme (used here) | 8.2 pips | 0.450 | **+0.262** |
| MSS origin | 1.2 pips | 0.342 | -1.538 |
| zone far edge (the KB advice) | 0.7 pips | 0.368 | -1.997 |

The overlap zone is often under a pip tall, so a zone-edge stop makes commission roughly
100% of risk. The advice is sound for a zero-cost chart and wrong for a real account.

## Confluences tested and rejected

Nineteen single-rule arms, then 54 combinations. These did not survive: OTE 62-79% gate
(-0.16 E[R]), premium/discount gate (-0.02), breaker-as-body (-0.03), swing n=5 (-0.04),
entry at CE (-0.004), leg displacement >= 1-3 ATR (no effect), 1R and 1.5R targets.
NY killzone works but is thinner than London. **Only the killzone time filter helped.**

## Loss-reduction rules mined from the repos - all four rejected

Encoded in `models/bt3.py`, each measured alone, in-sample, at 0.7 pip commission.

| Rule | Source | IS n | WR | E[R] | PF | Verdict |
|---|---|---|---|---|---|---|
| BASE (2R) | - | 94 | 0.479 | +0.295 | 1.52 | - |
| **LR1** failed-breaker early exit | `08-breaker-blocks/failed-breaker.md` | 95 | 0.295 | +0.092 | 1.20 | REJECTED - exits 47 trades that recover |
| **LR2** displacement score >= 10 | `09-displacement/displacement-strength-criteria.md` | 36 | 0.500 | +0.348 | 1.63 | helps, but n collapses to 36 |
| **LR3** HTF (H1) bias must agree | `25-htf-bias/htf-bias-framework.md` | 56 | 0.518 | +0.394 | 1.75 | REJECTED - IS 1.75 -> OOS 1.32, below base OOS 1.39 |
| **LR4** 50% at 1R, stop to breakeven | `32-risk-management/partial-takes.md` | 94 | **0.585** | +0.097 | 1.22 | REJECTED - best win rate, worst money |

**LR4 is the clearest lesson in the project.** Taking half off at 1R lifts the win rate
from 47.9% to **58.5%** and cuts expectancy from +0.295R to +0.097R - a higher win rate
bought with two thirds of the profit. That is v1 postmortem mistake #2, "trusted raw win
rate", reproduced on demand.

**LR3 is the clearest lesson in overfitting.** Best rule in-sample, decays -1.14 PF into
out-of-sample, against -0.13 for applying no filter at all. Decay, not in-sample score,
separates a rule from a coincidence.

## What actually raised profit factor: the opposite of loss reduction

| target | WR | PF | total R | max DD | R/month | median hold | decay IS->OOS |
|---|---|---|---|---|---|---|---|
| 1R | 0.585 | 1.14 | +9.9 | - | +0.31 | 22 min | -0.09 |
| **2R** | 0.450 | 1.47 | +40.5 | -10.8 R | +1.27 | 45 min | **-0.13** |
| **4R** | 0.333 | **1.56** | **+60.4** | -17.7 R | **+1.89** | 74 min | -0.22 |
| 5R | 0.264 | 1.60 | +67.9 | - | +2.12 | - | -0.55 |

Letting winners run to 4R makes 50% more money **while losing more often**. Past 4R the
in-sample to out-of-sample decay climbs sharply, so 4R is the edge of what the data supports.

## Which to trade

**2R** if drawdown matters more than return - better risk-adjusted (3.75 R earned per R
of drawdown, vs 3.41), shorter holds, smaller losing streaks, lowest decay of any arm.
**4R** for the larger absolute return, if you can sit through -17.7 R and ten losses in a row.

## Honest limits

- **149 trades is a small sample.** Bootstrap CI on 2R expectancy is [+0.031, +0.508];
  the lower bound is near zero. The 4R CI is [+0.061, +0.775].
- Many configurations were searched (19 arms, 54 combinations, 4 loss-reduction rules,
  7 targets). The hold-out confirmed the in-sample pick and IS->OOS win-rate correlation
  across all 54 combinations was +0.709, but the selection is real and the numbers are
  optimistic by some unquantified amount.
- **The original goal was not met.** 44.97% at 2R or 33.3% at 4R, never 70% at 1R.
  No configuration anywhere reached 70%.
- Slippage beyond the modelled commission is not simulated. Limit entries help; stop-outs hurt.
- GBPUSD is materially weaker than the other two pairs at 4R (PF 1.21 vs 2.12 / 1.78).


---

# Deep dive on the annotated cases - every case-derived change rejected

Eight annotated Unicorn cases exist in the OpenMobius knowledge base
(`Education_-_ICT_(Updated)__75S4vwD4P1U_case_003` and `case_006`,
`rXMVPUZPw4A_case_001/002/003`, `The_Foundation__09_case_003/004/005`). All were read and
each concrete instruction in them was implemented and measured.

**1. "Stop just below the breaker block low."** Stated in four of the cases, and
`case_003` compares it head to head with a swing-high stop and concludes the breaker stop
reached 2R where the swing-high stop was stopped out. Tested as **30 variants**
(narrow and wide breaker readings x buffers 0-5 pips x targets 2R/3R/4R): **every one
loses money.** Best was PF 1.00, +0.2R.

The decisive comparison is at matched risk. Widening the breaker reading until its median
risk is 9.4 pips - essentially the same as the swept-extreme stop's 9.2 - still gives
**PF 0.85 against 1.47**. So this is not a commission artefact: on M5 FX the breaker level
is simply a worse invalidation point. brodenbeck's doctrine explains why - the swept
extreme is the *protected* level, "if the model's premise is true the algorithm should not
revisit it", whereas the breaker sits between entry and sweep and is routinely traded
through before the move runs. The cases are mostly NQ/ES; `case_003` is a single EURUSD
example, n=1.

**2. "Target the draw on liquidity - equal highs, previous day high/low."** Every case
targets a pool rather than a fixed R.

| target | n | WR | PF | total R | IS PF -> OOS PF |
|---|---|---|---|---|---|
| equal-high/low cluster | 143 | 0.566 | 0.78 | -9.4 | 0.79 -> 0.77 |
| previous day high/low | 116 | 0.276 | 1.59 | +55.7 | **2.05 -> 0.91** |
| fixed 2R | 149 | 0.450 | 1.47 | +40.5 | **1.52 -> 1.39** |

Equal-highs clusters sit too close - median hold 5 minutes. PDH/PDL looks like the best
rule in the whole project in-sample and is **losing money out-of-sample**. Same signature
as LR3. Fixed R survives; liquidity targeting does not.

**3. "Entry at the mean threshold on retest."** That is the `ce` entry mode: -0.004 E[R].
No effect.

The deep dive changed the setup once - but not through anything the cases advise. Reading
them forced a look at where the losses actually sit, and that produced the 25-pip risk cap.
