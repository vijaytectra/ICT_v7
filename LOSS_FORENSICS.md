# Why the losses lose — trade forensics on the locked Asian-range model

Every trade replayed bar by bar on M1. Both periods, independently: **2024-2026**
(9 instruments, 395 trades) and the **2015-2023 holdout** (3 indices, 402 trades, nine
years the model has never seen). Code: `models/forensic.py`, `models/manage.py`,
`models/funnel.py`, `models/expand.py`. Raw data: `reports/forensic_*.csv`.

The instrumented executor reproduces the locked result exactly — n=395, PF 1.2940,
+87.932R — so these are the locked model's own trades, not an approximation.

---

## 1. The losses are two different animals, not one

| MFE reached before dying | 2024-26 | 2015-23 |
|---|---|---|
| **< 0.25 R** — filled and never moved | **34.8 %** | 31.4 % |
| 0.25 – 1.0 R — moved a little, reversed | 33.3 % | 33.6 % |
| **≥ 1.0 R** — went 1R+ in profit, gave it all back | **31.9 %** | **35.0 %** |
| … of which ≥ 2.0 R | 15.0 % | 13.8 % |

Median MFE on losses: **0.52 R / 0.56 R**.

A third of the losses are a *selection* failure — the read was wrong from the first bar.
A third are a *management* failure — the read was right and the trade was not banked.
The middle third is the market simply going the other way, and nothing recovers those.

## 2. The stop cannot be moved in either direction

**Tighter is impossible.** Median MAE on WINNERS is **−0.35 R / −0.42 R**, and
**10.9 % / 18.6 %** of winners dipped past −0.75 R before paying. Tightening kills the
winners before it saves the losers.

**Wider is worse.** 52.4 % / 57.2 % of stopped trades reached the original target within
24 h, which looks like a stop-placement problem until you measure how far price went
first:

| overshoot past the stop, on trades that later reached target | 2024-26 | 2015-23 |
|---|---|---|
| 25th percentile | 0.65 R | 0.63 R |
| **median** | **2.40 R** | **1.76 R** |
| 75th percentile | 4.43 R | 4.24 R |

| stop widened by | revisits saved |
|---|---|
| +0.20 R | 8.4 % / 9.3 % |
| +0.50 R | 17.5 % / 21.0 % |

To catch half of them the stop would have to be **2.4 R wider** — risking 3.4 R to make
3.2 R. The median gap between the stop-out and the target being reached is **320 / 270
minutes**. That is not a wick; it is a different move, hours later. We are not being
shaken out — price genuinely leaves, then comes back.

## 3. The "require a closing print" doctrine is measured and rejected

SrsBlack `08-breaker-blocks/failed-breaker.md`: *"a wick through the zone followed by
recovery is NOT a failure — require a closing print."* 50.2 % of stop-outs are wicks
(the bar closes back on our side), and wick stop-outs revisit the target more often
(57.7 % vs 47.1 %), so the doctrine looks directly applicable.

Simulated with the stop only triggering on an M15 close through the level:

| | live PF | holdout PF |
|---|---|---|
| locked | 1.294 | 1.213 |
| close-only stop | **0.953** | **1.059** |

Mean loss becomes **−2.14 R** (worst −26 R; 29 trades beyond −3 R), because by the time
an M15 bar closes through the stop, price is already a median 2.4 R past it. This
reproduces v2's LR1 result on a different model — the same doctrine, rejected twice.

> A first pass of this test booked the exit at the stop level instead of the actual
> close and produced PF **1.857 / 1.944**. That bug is recorded here deliberately: it is
> exactly what a plausible, doctrine-backed, +0.6 PF "improvement" looks like when the
> exit price is wrong.

## 4. Management cannot harvest the 32 % — and here is the arithmetic

Nineteen management rules simulated on the real M1 path — breakeven at 1/1.5/2/2.5 R,
profit locks, partials at 1 R and 2 R, four trailing schemes, three time stops, and the
close-only stop. **Not one improved both periods.**

Why, exactly:

| once MFE reaches | n | → win | → loss | E[R] of cohort |
|---|---|---|---|---|
| 1.0 R | 209 | 119 | 90 | +1.394 |
| 2.0 R | 163 | 119 | 44 | +2.094 |

Of the 209 trades that reached +1 R, 119 went on to target at **+3.25 R each** and 90
came back and died at −1.09 R.

- rescuing all 90 losers at breakeven saves **+98 R**
- clipping just **25 %** of the 119 winners costs **−97 R**

Breakeven has to be nearly perfect to break even. Measured, BE at 1 R takes PF from
1.294 to **1.098**. And the losers that reached +1 R had already reached a median MFE of
**1.98 R** before dying — so a breakeven stop at 2 R does not catch them either.

**Winners and near-miss losers share the same path shape and are indistinguishable until
the end.** That is not a defect to be fixed; it is what a 30 %-win-rate, 3.7:1 model is.

## 5. Where the trades actually go — the funnel

4,903 raw signals become 395 trades (8.1 %).

| stage | lost | share |
|---|---|---|
| **draw-on-liquidity pool closer than 2 R** | **2,000** | **40.8 %** |
| entry on the wrong side of the stop | 908 | 18.5 % |
| cost > 20 % of risk (Screen 2) | 746 | 15.2 % |
| limit never filled in 6 h | 634 | 12.9 % |
| no unswept pool in front | 92 | 1.9 % |
| Monday | 76 | 1.6 % |
| pool further than 10 R | 49 | 1.0 % |
| **crowded out by an open position** | **3** | **0.1 %** |

**The one-position-at-a-time rule costs three trades in 32 months.** Relaxing it is not a
lever — an assumption worth deleting.

The volume sits in four cohorts, each rejected for a different reason and therefore
needing a different alternative rule. They are **additive**: the locked 395 are
untouched, so anything kept runs as a second book with no trade-off against the first.

## 6. The four funnel cohorts, traded with alternative rules — three dead, one too small

Each rejected cohort was traded as a SEPARATE additive book, so the locked 395 are never
diluted. Fifteen arms, both periods:

| cohort | arm | live n | live PF | holdout PF |
|---|---|---|---|---|
| **A** rr_low (2,000 signals) | fixed 1 R | 923 | **0.908** | 0.888 |
| A | fixed 1.5 R | 914 | 0.922 | 0.873 |
| A | fixed 2 R | 907 | 0.815 | 0.832 |
| A | fixed 3 R | 896 | 0.733 | 0.829 |
| A | fixed 4 R | 893 | 0.650 | 0.687 |
| **B** bad_R (908 signals) | any entry | 1–4 | — | no volume |
| **C** no_fill (634) | first touch, 2 R | 25 | 5.957 | 20.544 |
| **D** cost (746) | first touch, zone stop, 2 R | 32 | 1.012 | 1.163 |

**Cohort A is the finding.** Two thousand signals, ~900 tradeable, and every target from
1 R to 4 R loses money in **both** periods with P(edge) between 0.000 and 0.12. So the
`min_rr ≥ 2.0` gate is not an arbitrary threshold that costs volume — the setups it
rejects are genuinely worse. When the draw-on-liquidity pool sits closer than 2 R the
structure is compressed, and that compression predicts failure whatever the exit.

Cohort C's PF of 5.96 / 20.54 on n=25 is not a discovery; effect sizes that large on a
model whose base is 1.29 are the shape of a small-sample artefact. Tested properly, at
full population, first-touch entry gives live PF **1.103** against the locked 1.294 and
holdout 1.213 against 1.213 — worse live, level on the holdout. The idea is dead.

## 7. Two mechanism-first selection hypotheses — one inverted, one dead

Blind scanning was stopped after 10 of 14 candidate filters failed the holdout. These two
come from the source material naming them as decisive, and neither had ever been applied
to this model.

**H2 obstruction — dead.** An unmitigated opposing H4 FVG sits between entry and target
on 94 % of trades. It is not a discriminator.

**H1 SMT — replicates, with the sign REVERSED.**

| | 2024-2026 | 2015-2023 holdout |
|---|---|---|
| SMT present (a peer did NOT raid its own bound) | PF 1.181, +23.9 R, n=174 | PF **0.819**, −25.5 R, n=166 |
| SMT absent (the whole group raided together) | PF **1.384**, +64.0 R, n=221 | PF **1.550**, +90.9 R, n=236 |

`smt-confirmation.md` calls SMT "the single highest-quality confluence factor". On this
model it is the opposite, in both periods.

The mechanism is consistent once the setup is taken seriously: this is a **session-range
raid**, not a swing-extreme reversal. When all three indices take out their Asian lows
together, the whole complex has run sell-side liquidity — a real, broad, algorithmic
event. When only ours does, the instrument is being idiosyncratically weak and there is
no coordinated sweep behind it. Divergence at a swing extreme and divergence at a session
bound are not the same object, and the corpus's SMT teaching is about the former.

Full effect of requiring SMT absent, on Arm A:

| | n | per month | WR | PF | totR | maxDD | R per R of DD | streak | P(edge) |
|---|---|---|---|---|---|---|---|---|---|
| locked, live | 395 | 12.3 | 0.301 | 1.294 | **+87.9** | −20.95 | 4.20 | 12 | 0.983 |
| SMT-filtered, live | 221 | 6.9 | 0.308 | **1.384** | +64.0 | **−13.77** | **4.65** | **9** | 0.977 |
| locked, holdout | 402 | 3.7 | 0.281 | 1.213 | +65.4 | −30.74 | 2.13 | 15 | 0.941 |
| SMT-filtered, holdout | 236 | 2.2 | 0.339 | **1.550** | **+90.9** | **−16.92** | **5.37** | 14 | **0.997** |

Better profit factor, better drawdown, better risk-adjusted return and a shorter losing
streak in **both** periods — bought with **44 % fewer trades**, and **lower total R on the
live period** (+64.0 against +87.9). On Arm B (shorts) it is inconsistent: live PF
1.665 → 1.528 (worse), holdout 1.476 → 1.726 (better). Not adopted.

---

## What this rules out

- widening the stop
- tightening the stop
- breakeven at any level
- partials at any level or fraction
- trailing at any distance
- time stops
- close-based ("no wick") stops
- relaxing the one-position rule

Each was measured on both periods. None survived.

- the rr_low cohort at any fixed R (2,000 signals, both periods, P(edge) ≤ 0.12)
- the bad_R cohort at any entry (no tradeable volume)
- first-touch entry instead of consequent encroachment
- an obstruction filter on opposing HTF arrays

## The one thing that replicated, and its price

Requiring **SMT absent** — the whole correlated group raiding its session bound together
— improves profit factor, drawdown, risk-adjusted return and losing streak in both
periods. It costs **44 % of the trades** and **27 % of live total R**. It is a genuine
quality-for-volume trade, not a free improvement, and it does not hold on the shorts-only
arm.

## The honest bottom line

Roughly **90 distinct configurations** were measured across two independent periods in
this study — 19 management rules, 15 additive-cohort arms, 2 entry variants, 2 selection
hypotheses, plus the 14 filters, 11 target variants and 26 lock mutations from the
earlier passes. Two things replicated: **skip Monday** (adopted, it costs only 17 % of
trades and improves every metric) and the **SMT filter** (a real trade-off).

Everything else failed, and the failures share one cause. The model's winners and its
near-miss losers have the same path shape — median MAE on winners −0.35 R, median MFE on
losses +0.52 R, a third of losses reaching 1 R or better. There is no boundary in the
path to cut on, and the R:R gate has already done the selection work at entry. A
30 %-win-rate, 3.7:1 model that survives its own nine-year holdout is close to what this
signal supports. The remaining uncertainty is not in the backtest.
