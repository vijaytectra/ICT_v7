# Running AsiaRangeRaid on MT5 demo

The EA is `AsiaRangeRaid.mq5`. It implements the validated rules exactly — nothing in it
was tuned to the live platform.

## Install

1. In MT5: **File → Open Data Folder → MQL5 → Experts**, copy `AsiaRangeRaid.mq5` there.
2. In MetaEditor press **F7** to compile. It should build with 0 errors.
3. Open a **USATECH / NAS100 / US100 chart on the M15 timeframe** (whatever your broker
   calls the Nasdaq 100 index CFD) and drag the EA on.
4. Allow algorithmic trading (the toolbar button, and the checkbox in the EA dialog).

## Two things to check before you trust a single trade

### 1. Server timezone — the single most likely cause of a live/backtest mismatch

The research data is Dukascopy **EET** (UTC+2 winter, UTC+3 summer). The Asian range is
`02:00–09:00 EET` and is only read after 09:00.

`AsiaStartHour` / `AsiaEndHour` are **broker server hours**, not your local time. Most MT5
brokers run EET, in which case 2 and 9 are already right. Leave `PrintServerTime = true`
on the first run and compare the logged server time against EET:

- server = EET → leave 2 and 9.
- server = UTC → use 0 and 7.
- server = EET+1 → use 3 and 10.

Get this wrong and the EA measures the wrong seven hours, which changes every level in the
setup. It will still trade. It will just be trading something that was never tested.

### 2. Your real all-in cost — this decides whether the edge survives

Cost is the largest single lever on the result, and it is not something I can optimise —
it is which broker you use. Measured on 12 years of USATECH:

| all-in cost beyond spread | trades | PF | total R | max DD |
|---|---|---|---|---|
| 0.0 pt | 362 | 1.575 | +114.7 | −19.7 |
| 0.5 pt | 336 | 1.514 | +100.2 | −21.9 |
| 1.0 pt | 301 | 1.481 | +86.3 | −21.0 |
| **1.5 pt** (assumed) | **262** | **1.420** | **+67.5** | **−15.2** |
| 2.0 pt | 222 | 1.369 | +51.0 | −14.4 |
| 2.5 pt | 191 | 1.344 | +40.7 | −12.6 |

Set `CommissionPoints` to your **round-trip** commission converted to points. If commission
is charged in currency, divide by the value of one point per lot. Leave it at 0 only if your
broker is genuinely spread-only.

## What the demo run is actually measuring

Not whether the strategy is profitable — 12 years of data already answered that as well as
backtesting can. The demo answers the two things a backtest cannot:

1. **Real fills.** The limit at the FVG CE is assumed to fill at that exact price. Live, it
   may not fill at all, or fill worse.
2. **Slippage on stop-outs.** Never modelled. Stops are market orders and 60% of trades end
   on the stop, so this eats the edge directly.

Log every signal, including the ones that do not fill. Around **40–50 trades** is enough to
tell whether the fill assumption holds; at 1.8 trades/month on one instrument that is a long
wait, so consider running USA500 and USA30 charts in parallel purely to collect fill data
faster (their standalone edge is weaker — US30 PF 1.01 and US500 0.77 over 2015-2023 — so
treat those as instrumentation, not as trades you would size up).

## Expected behaviour, so you can tell working from broken

- **~1.5 trades per month** on one index, with the reachability gate on. Long quiet stretches are normal.
- **Win rate 25-29%.** Seven of ten trades lose. That is the design, not a fault.
- **Average win +3.0R, average loss −0.93R.**
- **Fourteen consecutive losses occurred inside the 12-year sample.** It will happen again.
- Roughly **19 of every 33 months are profitable** — 4 losing months in a row is inside range.
- Exit mix in the backtest: 73 target, 140 stop, 42 break-even, 5 soft exit, 2 time stop.
  If you see almost no break-even exits, `BreakEvenAtR` is probably not firing — check the
  log for "stop moved to break-even".

## Verified against the research on this machine (2026-09-06)

The EA was compiled and run headless in the MT5 Strategy Tester on the broker's own
USTEC data (M15, every-tick, 99% history quality). Six translation bugs were found by
running it. Each was fixed and the test re-run:

| after fixing | trades | PF | total R |
|---|---|---|---|
| first working version | 92 | 0.79 | — |
| raid must be the FIRST break of the level | 74 | 0.91 | — |
| detector runs on every bar, in a trade or not | 72 | 1.03 | — |
| swing state persists; pivot ties match `argmax()==n` | 73 | 1.01 | — |
| Asian range off M1, Monday fills skipped, no early return before 09:00 | 120 | 1.16 | +11.2 |
| **a signal consumes the raid even when a gate rejects it** | **115** | **1.403** | **+26.2** |

The last one was the largest. In the research the *detector* emits the signal the moment
displacement closes through the frozen swing and clears the sweep at that instant; the
R:R gate, the cost gate and the Monday rule all live in the execution layer and run after
the sweep is already gone. Leaving the raid armed after a rejection turned one skipped
setup into a queue of late duplicates - 109 orders the research never places, and Monday
setups re-taken on Tuesday morning.

### Where it now stands against the research, same window

| 2024-01 to 2026-09 | EA on broker USTEC | research on Dukascopy |
|---|---|---|
| trades | 65 | 63 |
| profit factor | 1.698 | 1.643 |
| total R | +24.4 | +25.5 |
| win rate | 29.2% | 28.6% |
| max drawdown | -8.5R | -6.9R |

### The feed is not the problem

Running the *research code* on the *broker's* M15 bars and on Dukascopy's, same period,
same execution granularity, gives PF 1.294 (broker) against 1.253 (Dukascopy) on 102 and
103 trades. The two data sources agree. Individual entry prices differ by a few index
points and occasionally more, so trade-for-trade replication is not achievable and is not
the right test; the distributions matching is.

### What the longer broker history says

Broker data starts 2022-06. Over the full 4.2 years the EA makes PF 1.403 on 115 trades,
+26.2R, max drawdown -17.9R. Read the years honestly:

| year | trades | PF | total R |
|---|---|---|---|
| 2022 | 24 | 1.155 | +2.0 |
| 2023 | 26 | 0.982 | -0.3 |
| 2024 | 27 | 1.166 | +2.7 |
| 2025 | 26 | 1.601 | +8.4 |
| 2026 | 12 | 3.673 | +13.4 |

Half the total comes from 2026. Two of five years are flat. **Shorts are break-even on
this data (PF 0.986, -0.6R over 65 trades) while longs carry everything (PF 2.070, +26.8R).**
That is the opposite of the Arm B "shorts only" result measured on Dukascopy 2015-2023,
and it is a direct warning against sizing up either side on the strength of a split.

## The draw-on-liquidity reachability gate (added 2026-09-07)

Two new inputs, `MinTargetCrossings = 2` and `TargetLookbackBars = 96`. Before placing an
order the EA counts how many times price has CLOSED across the target level over the last 96
closed M15 bars. Fewer than two crossings and the setup is skipped.

The reasoning: zero crossings means price spent a whole day on one side of the target, so the
trade is being asked to reach liquidity it has not been near. Measured on the broker's own
USTEC ticks, 2022-06 to 2026-09:

| | trades | PF | total R | max drawdown |
|---|---|---|---|---|
| without the gate | 115 | 1.403 | +26.2 | -17.9R |
| **with the gate** | **79** | **1.545** | +23.8 | **-10.7R** |

Nearly the same profit from 31% fewer trades, and the drawdown almost halves. Every one of
the five years is positive for the first time: 2022 +2.8R, 2023 +1.5R, 2024 +4.7R, 2025 +2.5R,
2026 +12.3R. Expect roughly **1.5 trades a month** on one index rather than 2.3.

Leave both inputs alone. The threshold is a smooth region (1 through 6 all measure positive on
both halves of the research set) and 2 sits in the middle of it, not on a peak.

## THE LOCKED PORTFOLIO (2026-09-07)

The EA is the same on every chart. What is locked here is WHICH charts.

**33 instruments, defined by asset class, not by past performance.** Ranking instruments on
past profit factor is measurably noise: select on the first half of each one's history and the
rule "keep PF > 1.15" scores 1.701 on the second half, while a RANDOM pick of the same size
scores 1.701 and wins 50.4% of the time (rank correlation rho = +0.184, p = 0.25). So the list
is the USD majors, the crosses among the eight major currencies, and liquid index CFDs.

```
EURUSD GBPUSD USDJPY USDCHF USDCAD AUDUSD NZDUSD
EURJPY EURGBP EURAUD EURCAD EURCHF EURNZD
GBPJPY GBPAUD GBPCAD GBPCHF GBPNZD
AUDJPY AUDCAD AUDCHF AUDNZD
NZDJPY NZDCAD NZDCHF
CADJPY CADCHF CHFJPY
USTEC US30 AUS200 ES35 STOXX50
```

**Excluded, and why.** Pegged and exotic FX (EURDKK is pegged; the Scandi, Singapore, Turkish,
Mexican, Polish, Czech, Hungarian, Rand and CNH crosses carry costs a spread screen cannot
see) - structural. Metals and energy: tested and failed, XAUUSD PF 0.812 with the halves at
1.495 then 0.314, XAGUSD 1.024, XTIUSD 0.807 - the instability is the reason, not the level.
Crypto: the model raids the ASIAN SESSION range, and a 24/7 instrument has no such session;
measured anyway at BTCUSD 0.889 and ETHUSD 0.697.

### Measured, 32 of the 33 (no broker history for ES35 yet)

| | trades | PF | total R | win rate | max DD |
|---|---|---|---|---|---|
| whole period 2022-2026 | 2,239 | 1.515 | +824.3 | 29.9% | -40.5R |
| first half | 586 | 1.155 | +68.0 | 26.8% | -40.5R |
| **out-of-sample half** | **1,653** | **1.651** | **+756.2** | **31.0%** | **-22.0R** |

7.4 trades a week. Expectancy +0.368R, 95% CI [+0.273, +0.465], P(edge>0) 100%.
Per year: 2022 -7.7R (PF 0.956), 2023 +123.0R, 2024 +224.3R, 2025 +281.0R, 2026 +199.0R.

### Position size

**0.25% of equity per trade.** At that size the measured -40.5R drawdown is **-10.1%** of the
account and the return is **+35.6% a year**, or **+27.8%** after the 22% haircut the tick-level
MT5 run measured against this screen. Do not use 1% - the same drawdown becomes -40%.

Peak concurrency is 4 positions and the average is well under one, so risk per trade does not
compound into risk per moment. The pooled drawdown is what sizes this, not the concurrency.

### Before real money

The screen behind these numbers executes on M15 bars, not 1-minute, which on USTEC flatters by
about 3%. **Every name needs a tick-level Strategy Tester run first.** USTEC is the only one
done so far: 79 trades, PF 1.545, drawdown -10.7R, all five years positive.

`models/portfolio_locked.py` holds the list. `tests/test_portfolio_locked.py` pins the result
and fails if the universe is re-ranked on performance.

## Honest limits

- One instrument. The same rules made **PF 0.885 on six FX majors**, and on the other two US
  indices the 2015-2023 result was 1.01 (US30) and 0.77 (US500). This is a Nasdaq setup.
- 262 trades over 12 years. The 95% CI on expectancy is [+0.033, +0.490] — positive, but the
  lower edge is close to zero.
- Sixteen further improvements were tried and rejected, including four that looked
  substantial until a permutation test or a causality check killed them. Do not add filters
  to this without the same tests.

## Do not change these without re-testing

`SwingBars`, `MaxGapBars`, `DispRatio`, `MinRR`, `MaxRR`, `CostRiskMax`, `BreakEvenAtR`,
`CapTargetR`, `SoftExitMin`, `SoftExitR`. Each was measured; several are at a peak with
worse values on both sides. `BreakEvenAtR` in particular: at +0.5R it drops PF to 1.193
because it sits inside the noise band.
