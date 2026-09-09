# Locking the working model, and what actually raises its profit factor

2026-09-06. Written after the reach curve showed the Asian-range model is only viable at
1.5R and above. Everything below is selected on **DEV = the three US indices 2015-2023**
(nine years, the only long history in the project) and read once on **VAL = all nine
instruments 2024-2026**. The detector was never touched.

## The honest baseline

| | trades | PF | total R | win rate | max DD |
|---|---|---|---|---|---|
| DEV, 3 US indices 2015-2023 | 396 | 1.227 | +68.8 | 29.3% | -24.2R |
| VAL, 9 instruments 2024-2026 | 391 | 1.316 | +93.3 | 30.9% | -18.0R |

## What was tested, and what survived

| lever | DEV verdict | note |
|---|---|---|
| break-even at 1.5R | **drawdown only** | PF 1.227 -> 1.257 but total R +68.8 -> +63.9. Paired delta **-0.012R**, P(helps) 40.8% DEV / 46.8% VAL. Cuts drawdown on VAL and on the live MT5 run. |
| target capped at 6R | **no** | every cap from 3R to 8R is worse than no cap on DEV (1.242 -> 1.112-1.236). |
| soft exit at -0.5R after 15 min | **no** | DEV 1.257 -> 1.242. Adds nothing anywhere. |
| R:R gate raised 2.0 -> 2.4 | **not an edge** | PF 1.227 -> 1.317 and DD -24.2 -> -19.5, but permutation **p = 0.238** DEV / 0.578 VAL. It drops trades, it does not select better ones. Legitimate as risk management, not as an improvement. |
| max_rr tightened below 10 | **no** | monotonically worse: 1.317 -> 1.146 at max_rr 5. |
| CRI gate tightened below 0.20 | **no** | 1.317 -> 1.100 at 0.15. |

### The exit rules, settled properly

Run on the broker's own USTEC ticks in MT5, 115 trades 2022-2026, they give PF 1.403
against 1.254 without them and cut maximum drawdown from -27.1R to -17.9R. Paired on the
same trades the difference is **+0.043R, 95% CI [-0.129, +0.177], P(helps) 72.4%** - not
significant. Across the 787 research trades the paired delta is slightly negative.

So the fair statement is: **the exit rules do not add expectancy, but they do reduce
drawdown in most slices.** Keeping them is a defensible risk decision. Expecting them to
raise profit factor is not supported, and the "PF 1.296 -> 1.420" claim was one instrument.

**The exit rules were a USATECH result, not a general one.** On USATECH alone they do
replicate: 211 trades, PF 1.446 -> 1.566. Across all nine instruments they help on five and
hurt on four, and on the instrument with the most trades - **USA30, n=311** - they take PF
1.341 -> 1.315 and total R +80.1 -> +58.1. On DEV they take 1.227 -> 1.206. The earlier
"PF 1.296 -> 1.420" was measured on one instrument and does not generalise.

## What does raise the profit factor

Nothing in the exit or the gates. The only thing that survives is **which instruments you
run it on**, and that is decidable on DEV: USATECH 1.52, USA30 1.26, USA500 0.63.

**US30 + US100 (Nasdaq), locked config, no exit rules:**

| | trades | PF | total R | win rate | E[R] | max DD | P(edge>0) |
|---|---|---|---|---|---|---|---|
| DEV 2015-2023 | 368 | 1.249 | +69.8 | 29.3% | +0.190 | -24.2R | 96.1% |
| VAL 2024-2026 | 154 | **1.733** | +78.5 | 34.4% | +0.510 | -9.3R | 99.8% |
| **all 12 years** | **522** | **1.382** | **+148.3** | **30.8%** | **+0.284** | **-24.2R** | **99.8%** |

Out of sample is better than in sample. **Ten of twelve years are positive** (2016 -21.6R
and 2017 -1.2R are the exceptions). The other seven instruments together are 265 trades,
PF 1.065, +13.8R, P(edge>0) 66.6% - which is not evidence of an edge in either direction,
and for the six FX majors there is no long history to test on at all.

## Cost robustness, the thing the Unicorn lacked

| cost | DEV PF | DEV total R |
|---|---|---|
| half the assumed | 1.411 | +76.1 |
| **as assumed (1.5 index points)** | **1.317** | **+62.0** |
| 1.5x | 1.232 | +47.8 |
| 2x | 1.155 | +33.6 |
| 3x | 1.022 | +5.3 |

It stays above breakeven at three times the assumed cost. The Unicorn dies at 0.5 index
points. That difference, not the profit factor, is why this is the model being traded.

## The configuration this argues for

Detector and execution exactly as frozen in `models/asia_locked.py`: min_rr 2.0, max_rr 10,
CRI 0.20, draw-on-liquidity target, 6-hour order life, 24-hour maximum hold, Mondays skipped.
Instruments: **US30 and US100 only.** Keep the break-even and soft exit if you want the
smaller drawdown - on the MT5 run they take it from -27.1R to -17.9R - but do not count on
them for profit factor. Drop the 6R cap: it is worse than no cap everywhere on DEV.

Win rate is 30.8% and cannot be raised - the reach curve puts the model below breakeven at
every target of 1R and under. Higher profit factor here comes from removing instruments and
rules that were never supported, not from a better exit.

---

# CORRECTION, same day: the instrument ranking above was a cost bug

Everything above about "US30 + US100 only" rested on USA500 reading PF 0.63-0.98 on 28 DEV
trades. That was not a weak edge. `asia_locked.COST` charged a **flat 1.5 index points to
every index and 0.8 pips to every FX pair**, on top of the spread already inside the fills,
which is a different cost on every instrument:

| instrument | own median spread | flat charge | ratio |
|---|---|---|---|
| USATECH | 1.504 | 1.50 | 1.00x |
| **USA500** | **0.516** | **1.50** | **2.91x** |
| USA30 | 2.534 | 1.50 | 0.59x |
| **EURUSD** | **0.300** | **0.80** | **2.67x** |
| USDCAD | 1.200 | 0.80 | 0.67x |

USA500's median stop is 4.4 points, so a 1.5-point charge is a third of the risk. The CRI
gate then removed **72% of its setups - 1,636 valid signals down to 464** - and biased the
survivors towards the widest stops. The three indices produce almost identical raw signal
counts (2,156 / 2,103 / 2,129), so nothing about the market was different; only the fee was.

Cost is now `SPREAD_MULT * median_spread(sym)`, SPREAD_MULT = 0.4.

| | flat cost (bug) | fixed |
|---|---|---|
| DEV indices 2015-2023 | n=402, PF 1.213, +65.4R, DD -24.2 | **n=603, PF 1.233, +107.4R, DD -43.4** |
| VAL all nine 2024-2026 | n=395, PF 1.294, +87.9R, DD -18.4 | **n=532, PF 1.367, +141.2R, DD -18.0** |

Per instrument, everything that was over-charged improved and nothing that was under-charged
collapsed:

| | DEV before | DEV after | VAL before | VAL after |
|---|---|---|---|---|
| USA500 | 28 / 0.98 | **215 / 1.16** | 13 / 1.01 | **80 / 1.14** |
| USATECH | 151 / 1.32 | 163 / 1.42 | 63 / 1.67 | 68 / 1.70 |
| USA30 | 223 / 1.18 | 225 / 1.18 | 93 / 1.70 | 96 / 1.79 |
| USDCHF | - | - | 31 / 0.87 | **40 / 1.27** |
| USDCAD | - | - | 38 / 1.05 | **57 / 1.40** |
| GBPUSD | - | - | 44 / 1.05 | 54 / 1.19 |
| EURUSD | - | - | 39 / 0.96 | 56 / 1.03 |

Stable across the cost multiple: DEV PF 1.02-1.23 and VAL 1.35-1.38 for k from 0.2 to 1.0.

**So do not drop instruments.** The ranking that justified it does not exist once the fee is
measured in the same unit everywhere. The one real cost of the fix is drawdown: DEV goes
-24.2R to -43.4R on 50% more trades, so R per R of drawdown falls from 2.70 to 2.47.

`tests/test_asia_locked.py` now fails 59 pinned numbers, all of them computed through the
bug. Its two causality guards still pass.
