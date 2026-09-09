# The system, end to end

Everything in one place: how a trade forms, how it is taken, how it ends, what it has
actually produced, where the material came from, what has not been checked yet, and what
the alternatives cost.

---

# PART 1 — How a trade forms, explained simply

## The idea in one sentence

Overnight, while London and New York sleep, price drifts in a narrow band. Everyone who
trades that band puts their protective orders just outside it. In the morning, price
often pokes just past one edge, takes those orders, and then turns and runs the other
way. **We wait for the poke, wait for proof that it was a poke and not a real breakout,
and then join the turn.**

## The six steps

### Step 1 — Draw the overnight box (02:00–09:00 EET)

From 2 a.m. to 9 a.m. European time, mark the **highest** price and the **lowest** price.
That is the box. Nothing else matters yet.

*Rule:* the box may not be used until 09:00. Before 09:00 the box is still being drawn,
and using a half-drawn box means using information that did not exist yet. That single
mistake once produced a false profit factor of 1.43 in this project.

### Step 2 — Wait for the poke (the raid)

Price must trade **below the bottom of the box** having been above it on the previous
15-minute bar. That is a raid on the sell side, and it sets up a **buy**. (Mirror for a
sell: price pokes above the top of the box.)

The lowest price of that poke is written down. Call it the **raid low**. It becomes the
stop, and nothing else ever becomes the stop.

*Why:* the orders sitting under the box are fuel. Someone has to buy from the sellers who
just got stopped out, and that someone is the reason price turns.

### Step 3 — Wait for proof (displacement)

A poke alone is not enough — sometimes a break is a real break. So we wait for a
15-minute candle that:

- **closes above the swing high** that was the most recent confirmed high at the moment
  of the raid, and
- has a **body at least half the size of the whole candle** (a decisive candle, not a
  hesitant one).

That is the proof the poke has failed and price is being delivered upward again.

*Rule:* this must happen within **40 fifteen-minute bars** (10 hours) of the raid. If it
does not, the setup is dead and the raid is forgotten.

### Step 4 — Find the doorway (the fair value gap)

Inside the run from the raid low up to the proof candle, find the **first** place where
three consecutive candles leave a gap — candle 1's high is below candle 3's low, with
nothing traded in between.

That gap is the doorway. Its **exact middle** is where we place the order.

*Why the middle:* price that leaves a gap in a hurry usually comes back to fill about
half of it before continuing. The middle is where the buying and the selling balance.

### Step 5 — Place the order and wait

- **Buy limit** at the middle of the gap.
- **Stop loss** at the raid low. No buffer, no rounding.
- **Take profit** at the nearest **unswept pool** above — either the top of the overnight
  box, or yesterday's high, whichever is closer and has not already been taken today.
- The order lives **6 hours**. If price never comes back to the doorway, cancel it. Never
  chase.

### Step 6 — Five checks before it is allowed to exist

A setup is thrown away if any of these fails:

1. **Reward must be at least 2× the risk, and no more than 10×.** Too close means the
   structure is squashed; too far means the target is a fantasy.
2. **Cost must be under 20 % of the risk.** If the spread plus commission eats a fifth of
   what we are risking, there is nothing left to win.
3. **The target must have been visited.** Count how many times price has *closed* across
   the target level in the last 96 bars (24 hours). It must be **at least twice**. If
   price has spent a whole day on one side of the target, we are asking it to reach
   somewhere it has not been near.
4. **Not Monday.** Monday is the only losing day of the week, in both test periods
   independently.
5. **One position at a time per instrument.** No stacking.

### How it ends

- **Target hit** → win, typically +3.3× the risk.
- **Stop hit** → loss, −1× the risk plus costs.
- **Neither after 24 hours** → close it and move on.

No breakeven stop. No partial exits. No trailing stop. All three were tested; all three
cost money — see Part 4.

## What one trade looks like

```
        yesterday's high  ─────────────────────────  ← target (unswept pool)
                                            ╱
                                      ╱╱╱╱╱
   top of box  ────────────────────╱──────────────
                                 ╱   ← proof candle closes above the swing high
                              ╱
                     ▓▓▓▓  ← the gap; buy limit at its exact middle
                   ╱
   bottom of box ─╲────────────────────────────────
                   ╲╱  ← the poke.  Its lowest point is the stop.

   risk  = entry − stop          reward = target − entry
   the trade only exists if reward is between 2x and 10x risk
```

---

# PART 2 — What it has actually produced

## The instruments

**33 instruments, chosen by asset class, never by past performance.**

| group | count | names |
|---|---|---|
| USD majors | 7 | EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD, NZDUSD |
| major crosses | 21 | all crosses among EUR, GBP, JPY, CHF, CAD, AUD, NZD |
| index CFDs | 5 | USTEC, US30, AUS200, ES35, STOXX50 |

**Excluded, and why:** pegged and exotic FX (structural — EURDKK is pegged, the
Scandi/Singapore crosses carry costs the screen cannot see); metals and energy (tested and
failed — XAUUSD PF 0.812 with halves 1.495 then 0.314, XAGUSD 1.024, XTIUSD 0.807; it is
the instability, not the level); crypto (a 24/7 instrument has no Asian session to raid —
BTCUSD 0.889, ETHUSD 0.697).

The universe is defined by asset class on purpose. Ranking instruments on past profit
factor was measured and it is **noise**: first-half to second-half rank correlation
rho = +0.184, p = 0.25, and a random pick of the same size beats the "best" pick 50.4 % of
the time.

## The results

Broker M15 data, 2022–2026, 32 of the 33 (no broker history for ES35 yet):

| | trades | PF | total R | win rate | max drawdown |
|---|---|---|---|---|---|
| whole period | 2,239 | **1.515** | **+824.3** | 29.9 % | −40.5 R |
| first half | 586 | 1.155 | +68.0 | 26.8 % | −40.5 R |
| **out-of-sample half** | **1,653** | **1.651** | **+756.2** | **31.0 %** | **−22.0 R** |

- **7.4 trades a week**
- Expectancy **+0.368 R**, 95 % CI **[+0.273, +0.465]**, P(edge > 0) **100 %**
- Per year: 2022 −7.7 R · 2023 +123.0 · 2024 +224.3 · 2025 +281.0 · 2026 +199.0
- Peak concurrency **4**, average well under one, mean pairwise monthly correlation
  **+0.025**

## Sizing

| risk per trade | max drawdown | return a year |
|---|---|---|
| **0.25 %** | **−10.1 %** | **+35.6 %** (+27.8 % after the 22 % tick-level haircut) |
| 0.50 % | −20.2 % | +71 % |
| 1.00 % | −40.5 % | +142 % |

**0.25 % is the recommendation.** A Monte Carlo on the actual R sequence puts the 5th
percentile drawdown at roughly twice what actually happened, so plan for the −10 % and be
unsurprised by −20 %.

## The one gate that earned its place

**DOL reachability**: the target must have been closed across at least twice in the last
96 bars.

| | trades | PF | total R | win rate | max DD |
|---|---|---|---|---|---|
| development set, gate off | 575 | 1.202 | +90.2 | 27.1 % | −52.4 R |
| **development set, gate on** | **368** | **1.523** | **+141.1** | **32.3 %** | **−16.8 R** |
| validation set, gate off | 532 | 1.367 | +141.2 | 28.6 % | −18.0 R |
| **validation set, gate on** | **370** | **1.712** | **+179.9** | **33.2 %** | **−13.5 R** |

Fewer trades and **more** total R — the only filter in the whole project that improved
profit factor, total R, win rate and drawdown at the same time, on both periods.
Permutation p = **0.0002** and **0.0000**. Every other filter scored p ≈ 0.25, meaning it
only dropped trades at random.

## Per instrument, sorted by trade rate

| instrument | trades | years | per week | win rate | PF | 1st half | 2nd half |
|---|---|---|---|---|---|---|---|
| USDCAD | 58 | 1.6 | 0.69 | 31.0 % | 1.559 | 0.626 | 2.958 |
| CADCHF | 48 | 1.6 | 0.57 | 29.2 % | 1.429 | 1.099 | 1.798 |
| US30 | 116 | 4.2 | 0.53 | 28.4 % | 1.073 | 0.751 | 1.444 |
| EURCHF | 104 | 4.0 | 0.51 | 31.7 % | 1.650 | 1.593 | 1.707 |
| GBPUSD | 100 | 3.9 | 0.49 | 26.0 % | 1.463 | 1.356 | 1.571 |
| EURCAD | 100 | 4.0 | 0.48 | 38.0 % | 2.206 | 2.358 | 2.064 |
| GBPCAD | 99 | 4.0 | 0.48 | 29.3 % | 1.523 | 1.859 | 1.224 |
| EURUSD | 97 | 4.0 | 0.47 | 32.0 % | 1.595 | 2.029 | 1.211 |
| USDCHF | 89 | 4.0 | 0.43 | 42.7 % | 2.147 | 1.765 | 2.577 |
| EURGBP | 85 | 3.9 | 0.42 | 30.6 % | 1.599 | 1.293 | 1.916 |
| STOXX50 | 84 | 5.7 | 0.28 | 28.6 % | 1.260 | 1.072 | 1.451 |
| USTEC | 56 | 4.1 | 0.26 | 37.5 % | 1.430 | 1.309 | 1.560 |

Full table in `reports/broker_screen.csv`.

---

# PART 3 — Where the material came from

## The three primary knowledge bases

| repo | what it gave |
|---|---|
| **brodenbeck1/ict_trading** | the four-phase market-maker curve; CISD definition; internal/external range liquidity; v4 Screen 2 (cost / structural risk ≤ 20 %); stop-placement doctrine (the swept extreme is the *protected* level); `smt_divergence.py` |
| **SrsBlack/ict-knowledge-library** | 250+ concept pages with citations — the 2022 model sequence, killzones, Asian range, power of three, market-maker trap, manipulation templates, draw-on-liquidity, failed-breaker, displacement criteria, partial takes |
| **OpenMobius knowledge base** | MMBM/MMSM concept cards, 1,282 annotated video cases, the ERL→IRL→ERL framing |

## The seventeen repositories audited for a high win rate

| repo | win rate | PF | verdict |
|---|---|---|---|
| GifariKemal/xaubot-ai | 82.4 % | 2.51 | **simulator bug** — see below |
| fallenpheonix23/ict-trading-bot (daily) | 52.1 % | 1.52 | real, 15 years |
| SiyabongaDlamini/SmartMoney.MQ5 | ~50 % | 1.20 | real, n=434 |
| fallenpheonix23 (hourly SPY) | 40.3 % | 1.43 | real, 2 years |
| islero/ICT-NT | 35.4 % | 1.34 | real, n=79 |
| MoAbdullahi/ICT_Strategy_Video_Extraction | 30.5 % | 0.98 | **"a coin flip"** — their own words |
| OPKYEI/ICT-Trading | "65–70 %" | none given | "accuracy 89–91 %" is a classification metric, not a win rate |
| silotabs, rcook0, lordgaruda, Semordzi-Eric, futureteck, dextergsm, zakariab0, Musyimi97, Aditya18487 | — | — | no measured results |

**The xaubot-ai finding is the most important one in this table.** It is the only repo with
a real research programme — 39 sequential experiments on XAUUSD M15, ~50,000 real MT5 bars,
~680 trades per config, logs committed. Its ladder climbs 72.2 % → 74.4 % → 81.8 % → 82.4 %
win rate at PF 1.42 → 2.51.

One asymmetry produces all of it, identical in all 39 files: **the take profit is checked
against the bar's high/low, so an intrabar wick books a full win, while the stop is only
checked on the bar close and at 50 % of max loss.** Wins on the wick, losses on the close,
at half size. Plus a non-causal Viterbi pass over the whole series for regime labels, and
no spread, commission or slippage in any run.

Then the same codebase traded live for one day: **42 trades, 42.9 % win rate,
−$97.78.**

That is the cleanest available demonstration that a 70–80 % win rate at PF above 2 is what
a **broken simulator** looks like, not what a good strategy looks like.

`tests/test_sim_invariants.py` now locks the three properties that make it impossible
here, and all three pass: a bar touching both barriers is scored a **loss**; a wick through
the stop that closes back inside still stops us out; a long fills on the **ask** and exits
on the **bid**.

**Also from that audit:** of fifteen repositories, **not one** contains a rule that measures
a property of the *target* or the *path to it* — which is the only class of filter that has
ever worked here.

---

# PART 4 — What has been tested and rejected

Roughly 150 configurations, always on two independent periods.

## Exits and management — nineteen rules, none survived

| rule | result |
|---|---|
| breakeven at 1 / 1.5 / 2 / 2.5 R | PF 1.294 → 1.098 at 1 R; none improved both periods |
| profit locks | worse |
| partials at 1 R and 2 R, 33 % and 50 % | see the win-rate table below |
| four trailing schemes | worse |
| three time stops | flat |
| close-only stop ("require a closing print") | PF 0.953 / 1.059 — mean loss becomes −2.14 R |
| wider stop | price overshoots the stop by a **median 2.4 R** before turning |
| tighter stop | winners have median MAE −0.35 R; 11–19 % dip past −0.75 R |

**Why management cannot help:** of 209 trades that reached +1 R, 119 went on to target at
+3.25 R each and 90 came back and died. Rescuing all 90 at breakeven saves +98 R; clipping
just 25 % of the 119 winners costs −97 R. Winners and near-miss losers have the same path
shape and are indistinguishable until the end.

## The win rate ↔ profit factor exchange rate, measured

Same trades, same entry, only the exit differs:

| structure | win rate | PF | total R |
|---|---|---|---|
| **no partial, whole position to target** | 32.2 % | **1.523** | **+137.3** |
| 33 % off at +1.5 R | 45.1 % | 1.332 | +70.3 |
| 33 % off at +1.0 R | 53.8 % | 1.233 | +41.6 |
| 33 % off at +0.5 R | 63.9 % | 1.255 | +30.3 |
| 50 % off at +0.5 R | **69.2 %** | 1.176 | +20.8 |

**A 69 % win rate is available. It costs 85 % of the profit.**

## The frontier — 136 configurations

Sweeping the reachability threshold, the R:R gate and the target across 136 cells, scoring
development and validation separately:

**Cells with win rate ≥ 50 % AND profit factor ≥ 2.0 on both halves: ZERO.**

| win rate | best PF available (worse of the two halves) |
|---|---|
| 55 % | 1.05 |
| 50 % | 1.34 |
| 45 % | 1.39 |
| 40 % | 1.41 |
| 35 % | 1.54 |
| 30 % | 1.52 |
| **20 %** | **1.73** |

**The mechanism is the flatness of the reach curve.** Price reaches 1.0 R before the stop
54.9 % of the time and 3.0 R 35.0 % of the time — tripling the target costs only 20 points
of hit rate. A flat curve means the implied profit factor *rises* with the target. The
population wants a big target and a low win rate. That is not a design choice; it is the
shape of the excursion distribution.

## The barrier race — why the ceiling exists

For every signal, does price reach +2 R before −1 R?

| target | measured (live / holdout) | driftless random walk |
|---|---|---|
| 1.0 R | 50.1 % / 50.3 % | 50.0 % |
| 2.0 R | 32.1 % / 32.5 % | 33.3 % |
| 3.0 R | 22.9 % / 23.8 % | 25.0 % |

Eight different stop placements were tested — from 2.2 to 26 units, a twelvefold range.
Every one landed within ±3 points of the theoretical value. **Barrier probability is
invariant to stop placement**, in real data, with real spreads.

Selection *can* lift it: the best combination found reaches 50.0 % / 53.3 % — PF 2.00 /
2.29 — but on **42 and 45 trades in nine and three years**, which is 0.09 trades a week.
The lift is real; the volume is not tradeable.

## Also rejected

- cost/risk gate tightened from 0.20 → 0.08: development PF **1.000**, live PF 2.173
  (opposite directions, classic overfit)
- minimum R:R lowered 2.0 → 1.5: worse at every cost level; those trades are worth
  development PF 1.053 and validation 0.972 on their own
- instrument selection (US30 + Nasdaq only): artifact, p = 0.25
- SMT divergence: works with the sign **reversed**, and costs volume
- first-touch entry instead of the gap midpoint: worse
- relaxing one-position-at-a-time: worth 3 trades in 32 months

---

# PART 5 — What has NOT been checked

Ordered by how much it could still matter.

### 1. Live execution — the big one
Not a single trade has been placed. Every number assumes the limit fills at the gap
midpoint, the stop fills at the stop, and the cost is what the schedule says. **None of
those three has been observed once.** Only USTEC has had a tick-level Strategy Tester run
(79 trades, PF 1.545, DD −10.7 R, all five years positive). The other 32 need one.

### 2. The M15 execution haircut
The screen executes on 15-minute bars rather than 1-minute. The one tick-level comparison
measured a **22 % haircut**. That is applied to the headline return, but only measured
once, on one instrument.

### 3. Broker history depth
Most of the 33 have data only from 2022. Nine instruments have under two years. USDCAD's
0.69 trades a week and PF 1.559 rests on 58 trades in 1.6 years.

### 4. Correlation in a crisis
Mean pairwise monthly correlation is +0.025 and peak concurrency is 4 — measured in a calm
regime. In March 2020 or a flash crash, 21 currency crosses are one trade. That has not
been stress-tested.

### 5. Path filters — the one class nobody has built
Of fifteen repositories, none measures a property of the target or the path to it. The one
filter that worked here (DOL reachability) is exactly that class. Variants not tried:
- how *recently* the target was crossed, not just how often
- whether the path to the target contains an opposing untouched level
- how much *time* price has spent on our side of the target
- the same count on a higher timeframe

### 6. Entry timing inside the doorway
Only the exact midpoint and the near edge were tested. The 62 % / 70.5 % / 79 % retracement
levels of the raid-to-proof leg have not been.

### 7. Second entries
When the first order expires unfilled after six hours, the setup is discarded. Whether a
second doorway forms later in the same move has never been measured.

### 8. Session other than Asia
The box is always 02:00–09:00. The London range as the box for a New York raid has not
been tried.

### 9. Regime conditioning
No test of whether the edge differs by volatility regime, by trend/range classification, or
around scheduled news.

### 10. The cost model's slippage half
Commission is verified from the broker's published schedule. The slippage allowance is
**declared, not measured** — half a spread per round trip. Real slippage on the roughly
60 % of exits that are market stop-outs is unknown.

---

# PART 6 — Trading 8–10 instruments

The honest expectation, from 4,000 random subsets of the tradeable core:

| instruments | trades/week | PF median | PF 10th pct | PF 90th pct | P(PF < 1.2) |
|---|---|---|---|---|---|
| 5 | 2.06 | 1.394 | 1.106 | 1.674 | 20.1 % |
| **8** | **3.29** | **1.384** | 1.171 | 1.608 | 13.4 % |
| **10** | **4.13** | **1.381** | 1.200 | 1.578 | 9.9 % |
| 15 | 6.20 | 1.378 | 1.248 | 1.526 | 3.4 % |
| 20 | 8.28 | 1.377 | 1.280 | 1.490 | 0.6 % |
| 35 | 14.48 | 1.377 | 1.377 | 1.377 | 0 % |

**Ten instruments gives 4.13 trades a week at an expected PF of 1.38.** That meets the
4–6 trades a week requirement.

Notice what breadth actually buys: the **median** profit factor is identical at every size
— 1.38 whether you run 5 or 35. What changes is the **spread**. At 5 instruments there is a
20 % chance of ending under PF 1.2; at 20 instruments, 0.6 %. Breadth does not raise the
edge, it raises the odds of *getting* the edge.

### The selection premium, shown deliberately

| pick | trades/week | PF |
|---|---|---|
| top 10 by past profit factor | 4.11 | **1.970** |
| **random 10** | 4.13 | **1.381** |

The 0.59 difference is **not edge**. It is the reward for having already seen the answers.
First-half to second-half rank correlation is rho = +0.184, p = 0.25 — a random pick beats
the "best" pick 50.4 % of the time. Anyone handing over "the ten best pairs" is handing
over that 0.59 as if it were real.

### If ten is the limit, choose them by structure, not by score

Cover different currency legs so the drawdowns do not line up: e.g. **EURUSD, GBPUSD,
USDJPY, USDCHF, USDCAD, EURGBP, EURCHF, GBPJPY, USTEC, US30** — 7 FX + 2 indices + 1 cross,
roughly 4.3 trades a week, expected PF ≈ 1.38, no instrument chosen for its past result.

---

# The bottom line

| what was asked | what the data supports |
|---|---|
| 4–6 trades a week | ✅ 4.13 at ten instruments, 7.4 at thirty-three |
| minimum 1:2 reward-to-risk, dynamic | ✅ average 3.7 R, gated between 2 R and 10 R |
| very few losing trades | ⚠️ 70 % of trades lose; the average loss is −1.09 R and the average win +3.3 R |
| profit factor above 2 | ⚠️ 1.515 across 33 instruments; PF 2 exists only on subsets too small to trade |
| win rate 70–80 % | ❌ 69 % is reachable and costs 85 % of the profit; the frontier has zero cells at WR ≥ 50 % with PF ≥ 2 |

The system is real: 2,239 trades, out-of-sample better than in-sample, P(edge > 0) 100 %,
1,200 of 1,200 random controls beaten, and a look-ahead-proof causality test.

It is a **30 % win rate, 3.3:1 machine**. Every attempt to convert it into a 70 % machine
has been measured, and each one either destroys the profit or destroys the sample.

**The next measurement is not another backtest.** It is a tick-level Strategy Tester run
on each instrument, then demo with every signal logged, then 0.25 % live.
