# Market Maker Buy / Sell Model + Trap — built from all three repos, and it has no edge

The MMXM was implemented as the three reference repositories actually specify it,
gated end to end, and measured under a pre-registration written before any number
existed (`models/PREREG_MMXM.md`).

**Result: 237 configurations across two pre-registered experiments, zero survivors.
On the pooled US indices, in-sample rank and out-of-sample rank are correlated
−0.26 in experiment 1 and −0.66 in experiment 2 — in-sample performance carries no
information about out-of-sample performance, which is the signature of a search over
noise. Every gate the doctrine specifies measured negative when isolated.**

The same harness, on the same data and the same split, reproduces the already-validated
Unicorn index setup at PF 1.24. So this is a property of the MMXM, not of the backtester.

---

## What was built

`models/mmxm.py` — the four-phase curve, detected prospectively, nothing read ahead:

| phase | rule | source |
|---|---|---|
| **A accumulation** | the POI: an unfilled **H4 fair value gap** (internal range liquidity) price is trading into, in discount (bull) / premium (bear), inside the H4 dealing range | OpenMobius `market_maker_buy_model.json` rules 1–2; brodenbeck `internal_external_range_liquidity.md` |
| **B manipulation** | inside the POI a sell-side pool is taken — last confirmed M15 swing low, or relative equal lows. Optionally measured off candle **bodies** not wicks | SrsBlack `market-maker-trap.md` c8, "all the volume is seen in the bodies… the liquidity is going to rest above it" |
| **C smart money reversal** | **CISD** — a close above the highest high of the consecutive down-close candles that made the manipulation low. That candle run is the order block | brodenbeck `change-in-state-of-delivery.md` |
| **D distribution** | redelivery internal → external: target the dealing-range extreme, or fixed R | brodenbeck `market-maker-models.md`, OpenMobius MMBM `trading_implication` |

The **market maker trap** is the gate, not a separate model: the phase-B break runs
*against* higher-timeframe order flow, so the retail trigger is the pool. That is
`require_bias` in the detector.

Execution (`models/mmxm_bt.py`): limit entry at the order block mean threshold, filled on
the M1 **ask** for longs and exited on the **bid**, stop at the swept extreme, one
position at a time, both barriers in one M1 bar counted as a loss. Real Dukascopy spread
is inside every fill.

## Guards — all three pass (`tests/test_mmxm_invariants.py`)

The v7 Unicorn's first pass was invalidated by a sweep-state latch that passed every
statistical check. So the numbers below were only looked at after:

1. **latched state** — synthetic series that makes an extreme early and trends away
   forever; a latching detector falls silent. PASS.
2. **prefix invariance** — the whole pipeline run on 60 % of the data and on 100 %;
   182 signals compared, every field identical. This is the causality proof. PASS.
3. **signal census** — 9 instruments, 8.7–11.2 signals/month, no empty quarter,
   first-half/second-half ratio 0.83–1.32. PASS.

## Stage 1 — 216 configs, US100 in-sample only

Median PF **0.899**. 46 of 153 scored configs above 1.0 — about what a coin flip on a
0.9-centred distribution produces.

## Stage 2–3 — the pre-registered keep rule

`IS PF > 1.10` **and** `OOS PF > 1.05` **and** ≥ 2 of 3 indices PF > 1.0.

| config | IS n | IS PF | OOS n | OOS PF | US100 | US500 | US30 | keep |
|---|---|---|---|---|---|---|---|---|
| D6 noDisc mt erl IDX | 82 | 1.232 | 49 | 0.920 | 1.108 | 0.918 | 1.117 | ✗ |
| D3 erlPOI mt erl ALL | 81 | 1.299 | 82 | 0.917 | 1.103 | 0.732 | 0.739 | ✗ |
| D3 erlPOI cisd erl ALL | 106 | 1.248 | 95 | 0.899 | 1.067 | 0.935 | 0.915 | ✗ |
| D5 equal cisd rr2 ALL | 106 | 1.319 | 75 | 0.696 | 1.029 | 0.786 | 1.029 | ✗ |
| **D5 equal edge rr2 ALL** | 102 | **1.443** | 72 | **0.516** | 0.988 | 0.980 | 0.924 | ✗ |
| …16 candidates in total | | | | | | | | **0 kept** |

The best in-sample config in the entire grid, PF 1.443, is **0.516** out of sample.

## The decisive number

All 216 configs scored on the pooled three indices, in-sample and out-of-sample:

| | median | max | above 1.0 |
|---|---|---|---|
| in-sample PF | 1.028 | 1.812 | 86 / 162 |
| out-of-sample PF | **0.775** | 1.255 | **9 / 162** |

- **Spearman r(IS PF, OOS PF) = −0.26.** Pearson −0.18. Picking the in-sample leader is
  *worse* than picking at random.
- mean decay across every config: **−0.238 PF**.
- the top ten by in-sample PF average **0.828** out of sample, against 0.778 for all
  configs — the in-sample winners are indistinguishable from the field.
- two configs cleared 1.0 in both halves. With 86 in-sample survivors and a 9/162
  out-of-sample hit rate, **chance alone predicts about 4.8**. Two is *below* chance.

## The one config that looked alive, and why it is not

`require_discount=off, entry=mean threshold, target=dealing-range extreme, London` —
IS 1.397 → OOS 1.247, +47.1R, and 15 of 20 neighbourhood variants profitable. It fails
on inspection:

- **win rate 11.3 %**, mean planned R:R **13.5** — this is not a trade model, it is a
  lottery ticket that pays 13R on one try in nine.
- **five trades out of 159 are 58 % of all gross profit.** Drop the single best trade and
  PF falls 1.334 → 1.083. Drop two and it is **0.895 — losing**.
- P(edge > 0) = **0.790**; the 95 % CI on expectancy is [−0.33, +1.07], straddling zero.
- USA30 is 0.987 — one of the three indices is already negative.

## Every gate the doctrine specifies makes it worse

Pooled indices, execution fixed at mean-threshold entry / 2R / NY AM killzone:

| arm | n | WR | PF | IS → OOS |
|---|---|---|---|---|
| **H3** POI = HTF FVG (internal range liquidity) | 241 | 0.286 | **0.802** | 0.860 → 0.734 |
| **H3** POI = none *(control)* | 563 | 0.302 | **0.858** | 0.957 → 0.751 |
| **H3** POI = external range liquidity taken | 189 | 0.307 | 0.887 | 0.973 → 0.800 |
| **H4** pool measured off wicks | 241 | 0.286 | **0.802** | 0.860 → 0.734 |
| **H4** pool measured off **bodies** | 258 | 0.279 | **0.773** | 0.876 → 0.659 |
| **H2** CISD, order block = candle bodies | 241 | 0.286 | 0.802 | 0.860 → 0.734 |
| **H2** CISD, order block = full range | 230 | 0.270 | 0.738 | 0.844 → 0.615 |
| **H2** CISD + displacement + FVG required | 132 | 0.235 | **0.614** | 0.696 → 0.545 |
| discount / premium gate off | 574 | 0.310 | 0.899 | 0.915 → 0.877 |
| HTF order-flow gate off | 505 | 0.329 | **0.979** | 1.054 → 0.907 |
| pool = relative equal highs/lows | 179 | 0.291 | 0.818 | 0.912 → 0.702 |
| no pool requirement at all | 292 | 0.291 | 0.821 | 0.874 → 0.758 |

Read the table plainly. **H1 rejected** — nothing is above 1.0. **H3 rejected** — the
ERL→IRL→ERL point-of-interest gate makes the model *worse* than no gate (0.802 vs 0.858).
**H4 rejected** — measuring liquidity off bodies, which the mentorship states explicitly,
is worse than wicks (0.773 vs 0.802). **H2 rejected** — adding the displacement and FVG
confirmation stack costs 0.19 PF. And the single largest gate in the whole doctrine, the
higher-timeframe order-flow read, is the one whose *removal* helps most (0.802 → 0.979).

Every arm decays from in-sample to out-of-sample. Not one exception.


## Experiment 2 — the amendment, and it changes nothing

Experiment 1 used a swing-pivot pool and no structural risk floor. Both were wrong, and
both are corrected by findings this project produced **before** the MMXM existed, not by
looking at MMXM output:

1. **The pool.** `ict-2022-model.md` step 3 names *time-defined* pools — Asian range,
   PDH/PDL, session extreme. A 3–5 bar swing pivot is inducement. Measured earlier here
   across nine instruments: Asian range PF **1.19**, both pools 1.02, PDH/PDL 0.76.
   Experiment 1 used the pool already known to be the weak one.
2. **The risk floor.** brodenbeck v4 Screen 2, cost / structural risk ≤ 20 %. Without it
   the population fills with setups whose entry sits on the sweep extreme — sub-pip
   stops, planned R:R in the hundreds, ~2 % win rate. Experiment 1's "survivor" had mean
   planned R:R 13.5 and an 11 % win rate: exactly that pathology, and it had no floor.

So: `sweep_pool='asia'` added to the detector, `max_cost_frac=0.20` to the executor, and
real cost now charged on top of the spread (FX 0.8 pip, index 1.5 pt) — **stricter** than
experiment 1. 24 configs: pool {asia, swing} x entry {mean threshold, edge} x target
{2R, 3R, ERL} x killzone {index AM, London}. All three guards re-run and re-passed first.

| config | n | WR | PF | IS → OOS | US100 | US500 | US30 | keep |
|---|---|---|---|---|---|---|---|---|
| swing · mt · ERL · IDX | 161 | 0.118 | 1.082 | 1.009 → 1.154 | 1.018 | 1.774 | 0.973 | ✗ |
| asia · mt · ERL · IDX | 135 | 0.126 | 1.048 | 1.193 → 0.900 | 1.260 | 1.485 | 0.686 | ✗ |
| asia · edge · 3R · IDX | 207 | 0.251 | 0.855 | 1.163 → 0.566 | 0.733 | 0.954 | 0.919 | ✗ |
| …21 configs scored | | | median **0.752** | | | | | **0 kept** |

**Spearman r(IS PF, OOS PF) = −0.656.** In experiment 1 it was −0.26; giving the model
its two best-known levers made the in-sample ranking *more* anti-informative, not less.
The two configs above 1.0 are the same tail-lottery shape — 11.8 % and 12.6 % win rates —
and neither passes the keep rule.

**237 configurations across two pre-registered experiments. Zero survivors.**

## The control that makes this believable

A negative result is worthless if the harness is simply pessimistic. So the validated
Unicorn index config from `SETUP_INDEX.md` was run through **this** backtester
(`models/control_mmxm.py`):

| | n | WR | PF | total | IS → OOS | P(edge>0) |
|---|---|---|---|---|---|---|
| Unicorn, indices, via mmxm_bt | 435 | 0.400 | **1.237** | +61.1R | 1.143 → **1.380** | **0.982** |
| documented in `SETUP_INDEX.md` | 413 | 0.356 | 1.21 | +52.8R | 1.18 → 1.25 | 0.967 |

Same instruments, same period, same split, same execution assumptions, the new code
path — and it reproduces. The MMXM's 0.80 is the MMXM.

## H5, the transfer test

| market | n | WR | PF | total |
|---|---|---|---|---|
| US indices | 159 | 0.113 | 1.334 | +47.1R |
| six FX majors | 358 | 0.148 | 0.938 | −18.8R |

Consistent with every prior result in this project: FX shows nothing. But the index side
is the fragile tail-lottery above, so this is not a transfer *result*, only a consistency
check.

## What to do with this

**Do not trade the MMXM.** Not at any of the 216 configurations tested, and not at the
one that looked alive.

What the doctrine got right and the data confirms elsewhere: the sweep-then-reverse
core. What it did not survive is everything layered on top of it — the internal/external
liquidity cycle, the HTF-FVG point of interest, CISD as a trigger, body-measured pools,
and the higher-timeframe bias gate. Each was implemented as specified, each was measured
alone, and each cost profit factor.

The setup in this repository that has survived every test put to it is still
[`SETUP_INDEX.md`](SETUP_INDEX.md) — the Unicorn on US100 / US500 / US30, PF 1.21–1.24,
out-of-sample better than in-sample, P(edge > 0) 96.7–98.2 %. Its honest limits are
listed on that page and they have not changed.

## Files

```
models/PREREG_MMXM.md        the pre-registration, written first
models/mmxm.py               detector - the four phases
models/mmxm_bt.py            M1 bid/ask execution, stats, bootstrap
models/mmxm_lab.py           loading, caching, IS/OOS slicing, pooling
models/run_mmxm.py           stage 1  - 216-config grid, US100 in-sample
models/corrob_mmxm.py        stages 2-3 - the keep rule
models/decide_mmxm.py        the IS-vs-OOS rank correlation
models/neighbourhood_mmxm.py the 20-variant region test + FX transfer
models/fragility_mmxm.py     jackknife + the H2/H3/H4 ablations
models/control_mmxm.py       the Unicorn control through this harness
models/amend_mmxm.py         experiment 2 - Asian-range pool + risk floor
tests/test_mmxm_invariants.py  latched state, prefix invariance, census
reports/mmxm_*.csv           every number above
```

---

# MMXM v2 — the four things v1 got wrong, fixed, and what changed

v1 was a partial reading of the repositories.  A systematic audit found four
structural omissions.  All four are now implemented (`models/mmxm2.py`) and all four
guards pass, including a prefix-invariance test that covers the SMT peer wiring.

| # | v1 did | the repos actually say | fixed in v2 |
|---|---|---|---|
| 1 | used an H4 FVG as the point of interest; **phase A was never implemented** | brodenbeck `market-maker-models.md`: "decompose: **consolidation detection** (range compression), leg counting away from it, then SMR". SrsBlack `range-contraction.md` gives criteria: `ATR_recent ≤ 0.7 × ATR_prior` AND `overlap_pct ≥ 0.7` AND no external BOS | accumulation range detected per session day, contraction test implemented verbatim |
| 2 | CISD + displacement FVG only | brodenbeck: SMR confirmation stack is "**SMT divergence**, MSS/CISD, displacement FVG". `index-smt.md`: "one index will fail to confirm a lower low — that's your bullish confirmation" | SMT implemented as brodenbeck's `smt_divergence.py` does it, anchored at a structural extreme: the peer must not have swept **its own** accumulation bound |
| 3 | generic 40-bar window for the manipulation | it is the **Judas swing**. `intraday-amd.md` fixes the windows: A 18:00→03:00 NY, M 02:00→05:00 NY, D 08:00→12:00 NY | manipulation gated to the London-open killzone |
| 4 | targeted the **H4** dealing-range extreme from an **M15** entry array | `market-maker-manipulation-template.md`: "the target array must sit on a timeframe **lesser** than the timeframe of the array used for entry" — the one rule it restates in every template | target is the **opposite bound of the accumulation range** — the engineered pool the cycle was built to reach |

## v2 results, 144 configs, pooled indices

| | v1 | **v2** |
|---|---|---|
| median PF (spread only) | 0.899 | **0.930** |
| configs above 1.0 | 46/153 | 11/144 |
| OOS above 1.0 | 9/162 | 1/144 |
| Spearman r(IS, OOS) | −0.26 | −0.19 |
| survivors of the keep rule | 0 | **0** |

Fixing the four omissions moved the median up 0.03 and changed nothing that matters.

**And all four doctrinal gates still measure negative** (mean PF over 72 configs each,
gate ON vs OFF, spread-only):

| gate | ON | OFF | delta |
|---|---|---|---|
| SMT divergence | 0.894 | 0.928 | **−0.034** |
| contraction test | 0.904 | 0.918 | **−0.014** |
| Judas time window | 0.901 | 0.921 | **−0.020** |
| HTF order flow | 0.859 | 0.963 | **−0.104** |

So it was not that v1 implemented them badly. Implemented exactly as specified, each
one costs profit factor.

## The one thing that did change — and why it is still not tradeable

The **best of the 144 is the fully ungated one**: Asian-range accumulation → sweep of
its bound → CISD → limit at the order-block mean threshold → stop at the swept extreme
→ target the opposite bound. No SMT, no contraction test, no Judas window, no bias.

Spread-only it looks strong, and — against every prior result in this project — the
strength is in **FX, not the indices**:

| | n | WR | PF | IS → OOS | P(edge>0) | 95% CI on E[R] |
|---|---|---|---|---|---|---|
| six FX majors | 4495 | 0.223 | **1.215** | 1.269 → 1.149 | **1.000** | [+0.086, +0.248] |
| US indices | 2624 | 0.234 | 1.062 | 1.129 → 0.973 | 0.856 | [−0.037, +0.133] |
| all nine | 7119 | 0.227 | 1.159 | 1.217 → 1.086 | 1.000 | [+0.063, +0.184] |

All six FX pairs positive, all six positive out of sample. That is a real signal in the
data — and it is **entirely inside the transaction cost**:

| extra cost | PF | IS PF | OOS PF | P(edge>0) |
|---|---|---|---|---|
| 0.0 pip | 1.215 | 1.269 | 1.149 | 1.000 |
| 0.4 pip | 1.110 | 1.163 | 1.045 | 0.989 |
| 0.5 pip | 1.086 | 1.139 | 1.022 | 0.961 |
| **0.7 pip** *(this project's standing assumption)* | **1.040** | 1.093 | **0.978** | **0.807** |
| 1.0 pip | 0.978 | 1.029 | 0.917 | 0.311 |

Median risk is **5.5–10 pips**. At that size 0.7 pip *is* 8–13 % of risk. Breakeven
sits at roughly **0.75 pip** — inside the range of a real retail commission. The
structural risk floor does not rescue it (OOS 0.922 at 0.7 pip with the floor on).

Per pair at 0.7 pip, only two of six are meaningfully positive:

| pair | n | PF | IS → OOS | P(edge>0) | median risk |
|---|---|---|---|---|---|
| USDCHF | 785 | 1.117 | 1.201 → 1.024 | 0.864 | 5.5 p |
| USDJPY | 621 | 1.146 | 1.239 → 1.036 | 0.819 | 10.2 p |
| GBPUSD | 797 | 1.027 | 1.105 → 0.929 | 0.598 | 8.2 p |
| AUDUSD | 686 | 0.997 | 0.992 → 1.004 | 0.480 | 5.1 p |
| USDCAD | 854 | 0.982 | 1.008 → 0.952 | 0.416 | 5.9 p |
| EURUSD | 752 | 0.996 | 1.046 → 0.926 | 0.478 | 6.4 p |

And it is fading: quarterly at 0.7 pip, **5 of 11 quarters positive**, with the last
three all negative (0.957, 0.923, 0.855).

## The comparison that settles it

This project already owns a better version of the same idea. The 2022 Asian-range model
(`models/ict_system.py`) is the same accumulation-sweep core, far more selective, and
measured **with cost already charged**:

| | n | PF (cost charged) | IS → OOS |
|---|---|---|---|
| 2022 Asian-range model | 471 | **1.19** | 1.28 → 1.09 |
| MMXM v2, best of 144 | 4495 | 1.04 | 1.09 → 0.98 |

Fifteen times the trades for a worse profit factor. The MMXM's phase machinery — SMT,
contraction, Judas timing, HTF bias, the ERL/IRL cycle — adds nothing on top of
"sweep the session range and reverse", and the selectivity it lacks is what the 2022
model has.

## Verdict after both versions

The audit was correct: v1 did not use the repositories properly, and four real
omissions were found and fixed with sources. Fixing them raised the median profit
factor from 0.899 to 0.930 and left the conclusion unchanged. **Do not trade the
MMXM.** Its ungated core has a genuine but sub-cost signal in FX that breaks even at
about 0.75 pip; the model's own doctrinal gates all subtract from it.

## Additional files

```
models/mmxm2.py                the corrected four-phase detector
models/mmxm2_lab.py            SMT peer wiring, caching, IS/OOS
models/run_mmxm2.py            the 144-config grid + gate ablation
models/best_mmxm2.py           deep dive on the grid's best config
models/cost_mmxm2.py           the cost sensitivity that decides it
tests/test_mmxm2_invariants.py 4 guards incl. accumulation-window causality
reports/mmxm2_*.csv
```
