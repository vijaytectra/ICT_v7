# 🔒 LOCKED — ICT 2022 Asian-range model

**Locked 2026-09-06. v2 added skip-Monday. v3 moved ARM B to the reclaim trigger + London-killzone raid; ARM A is unchanged.** Config frozen in [models/asia_locked.py](models/asia_locked.py).
Result pinned by [tests/test_asia_locked.py](tests/test_asia_locked.py) — 5 checks, all
passing. Evidence: [ASIA_MODEL_REPORT.md](ASIA_MODEL_REPORT.md).

Lock v1 reproduced `reports/asia_model_trades.csv` trade-by-trade identical (max netR
difference 4.4 × 10⁻¹⁶); **lock v2 adds one rule — skip Monday** — measured, validated on
a nine-year holdout, and re-pinned. See "Skip Monday" below.

```
python tests/test_asia_locked.py     exit 0 = the lock holds
```

---

## The rules — trade exactly this, nothing else

**Structure M15. Execution M1. Bullish shown; bearish mirrors.**

| # | rule | locked value |
|---|---|---|
| 1 | **Asian range** = high/low of **02:00–09:00 EET**. Usable **only from 09:00**. | `ASIA_EET = (2, 9)` |
| 2 | **Raid** — price trades **below the Asian low**, having been above it on the prior bar. Record `SL_px` = the raid low. | pool = **Asian range only** |
| 3 | **Window** — the next step must occur within **40 M15 bars**, else reset. | `max_gap = 40` |
| 4 | **Displacement** — an M15 candle **closes above the swing high current at the raid**, body / (high − low) ≥ 0.5. | `disp_ratio = 0.5`, swing `n = 5` |
| 5 | **FVG** — first 3-candle gap inside the raid→displacement leg. | — |
| 6 | **Entry** — resting limit at the FVG's **consequent encroachment** (50 % midpoint). Valid **6 hours**, then cancel. No chasing. | `entry = "ce"`, `window_min = 360` |
| 7 | **Stop** — `SL_px`, the raid extreme. No buffer. | `stop_buf = 0` |
| 8 | **Target** — the **draw on liquidity**: nearest unswept pool (Asian high, or PDH). **Never a fixed R. Never moved to fit.** | `target = "dol"` |
| 9 | **R:R gate** — skip if the pool is **closer than 2R** or **further than 10R**. | `min_rr = 2.0`, `max_rr = 10.0` |
| 10 | **Cost gate** — skip if all-in cost > **20 %** of stop distance. | `cri_max = 0.20` |
| 11 | **Fallback exit** — flat after **24 h** if neither barrier is hit. | `max_hold = 1440` |
| 12 | **Skip Monday.** Do not take an entry that fills on a Monday. | `SKIP_DOW = (0,)` |
| 13 | One position at a time, **per instrument**. | — |

### Gates deliberately switched OFF — each was measured and each costs money

| gate | PF with it | baseline |
|---|---|---|
| HTF daily bias required | 1.04 | **1.19** |
| trending-market profile | 1.00 | **1.19** |
| both | 0.92 | **1.19** |
| killzone window | 1.11 | **1.19** |
| short-term-low discriminator | 1.05 | **1.19** |

Independently replicated in the MMXM build: SMT −0.034, contraction −0.014, Judas
window −0.020, HTF order flow −0.104. **Two separately built models, same answer.**

### Instruments and costs

9 instruments: US100, US500, US30, EURUSD, GBPUSD, USDJPY, USDCAD, USDCHF, AUDUSD.
Cost charged on top of the real spread already in the fills: **0.8 pip** FX,
**1.5 points** index.

---

## Two arms, tracked separately

### ARM A — both sides *(the pre-registered model)*

| | |
|---|---|
| trades | **471** (14.7/month across 9) |
| win rate | 28.66 % · avg planned R:R 3.68 |
| expectancy | **+0.1463 R** · PF **1.1892** · total **+68.90 R** |
| max drawdown | −21.71 R · longest losing streak **14** |
| median stop | 12.45 units · median hold 40 min |
| IS → OOS | 1.3061 → 1.0495 |
| P(edge > 0) | 0.9374 · CI **[−0.0380, +0.3379]** ⚠ crosses zero |

Per instrument (n): US30 108 · US100 80 · GBPUSD 54 · USDCAD 46 · USDJPY 45 ·
AUDUSD 43 · EURUSD 42 · USDCHF 37 · US500 16. Six of nine profitable.

### ARM B — shorts only, **v3 detector**

Arm B runs a **different detector** from Arm A. Rules 1–3 and 5–13 are identical; rule 4
is replaced:

| | Arm A | **Arm B (v3)** |
|---|---|---|
| reversal trigger | close through the swing high current at the raid (full MSS) | **close back through the raided Asian bound** (`trigger='reclaim'`) |
| raid time | any hour ≥ 09:00 EET | **09:00–12:00 EET, the London killzone** (`raid_kz=(9,12)`) |

Sources: `market-maker-trap.md` variant 2 — a break below consolidation that reverses *is*
the accumulation event; `liquidity-sweep.md` — "close to it without sustaining the break";
`intraday-amd.md` — the Asian range is the accumulation for the **London** manipulation
(M = 02:00–05:00 NY).

| | |
|---|---|
| trades | **382** (11.9/month) |
| win rate | 31.68 % · avg planned R:R 3.95 |
| expectancy | **+0.3434 R** · PF **1.4650** · total **+131.18 R** |
| max drawdown | **−15.94 R** · longest losing streak **11** |
| median stop | 9.80 units · median hold 60 min |
| IS → OOS | 1.4833 → **1.4388** |
| P(edge > 0) | **0.9986** · CI **[+0.1248, +0.5777]** ✅ excludes zero |

Selected on **US indices 2015–2023 only**, then applied unchanged. Total R improved in
every slice:

| slice | locked trigger | v3 reclaim+London |
|---|---|---|
| indices DEV 2015-23 | 227 · 1.476 · +78.7 R | 319 · 1.457 · **+112.2 R** |
| indices VAL 2024-26 | 94 · 1.813 · +52.3 R | 139 · 1.657 · **+66.6 R** |
| FX VAL 2024-26 | 118 · 1.552 · +46.3 R | 243 · 1.357 · **+64.6 R** |
| all 9 VAL 2024-26 | 212 · 1.665 · +98.6 R | 382 · 1.465 · **+131.2 R** |

Profit factor is **lower** in all four; total R is **higher** in all four; trade count
roughly doubles. R per R of drawdown on the pooled validation set improves 6.78 → **8.23**.
Eight of nine instruments positive — **GBPUSD flips +11.5 R → −11.5 R** and is the one
genuine failure; it has not been removed, because dropping an instrument after seeing its
result is the cherry-picking that killed six earlier versions.

**The same change was tested on Arm A and REJECTED**: 1.294 → 1.050 on the validation
period, 1.072 → 0.979 on FX. Longs are the losing side (PF 0.906 over 11.7 years), so a
looser trigger adds mostly junk there. Full evidence: [V3_RECLAIM_RESULT.md](V3_RECLAIM_RESULT.md).

**Arm B is not a replacement for Arm A.** Side was not pre-registered. The forward test
decides.

---

## What the lock test pins

1. **Arm A** — all 13 statistics + per-instrument trade counts + IS/OOS, to 1e-4.
2. **Arm B** — same.
3. **`max_rr` is a region, not a point** — PF at 6/8/10/12/15 = 1.251/1.276/1.294/
   1.295/1.276. If any drops below 1.15 the parameter has become fitted and the lock
   must be reviewed.
3b. **The skip-Monday rule bites and its cohort is still negative** — Monday must remain
   76 trades at PF 0.708. If Monday ever stops losing, the rule loses its reason to
   exist and the lock must be reviewed.
4. **Asian-range causality** — the raid bar must sit at hour ≥ 09:00 EET, and every
   finite Asian level must belong to a session completed on or before that date.
5. **Prefix invariance** — the pipeline run on 60 % of the data vs 100 %; 452 signals
   compared, every field identical. This is the look-ahead proof.

## Known frozen behaviour — documented, not "fixed"

The 40-bar window is 10 hours, so a late raid can emit its signal after midnight,
before the next Asian session closes. `ah`/`al` refresh only at hour ≥ 09:00, so such a
signal carries the last completed session's levels — and carries NaN when that was a
weekend. When NaN, the draw-on-liquidity target falls back to PDH/PDL alone. This is
causal and is inside the measured result. Changing it invalidates the pinned numbers.

---

## Honest limits — read before risking money

- **Arm A's CI now excludes zero** ([+0.019, +0.434], P(edge) 98.3 %) — but that is
  after adding a rule found by scanning 13 features. The honest live expectation is
  lower than the measured 1.294.
- **The profit is still concentrated.** In lock v1, 2025 Q1 + Q2 alone were +71.1 R of
  the +68.9 R total. Skipping Monday does not fix concentration, it removes a
  loss cohort.
- **It still decays out of sample**, though far less: 1.334 → 1.243 (was 1.31 → 1.05).
- **The nine-year holdout is weaker than the recent period**: with Monday skipped,
  PF 1.213 and P(edge) 0.939, CI still touching zero at −0.040.
- Three of nine instruments lose money; two more are within noise of breakeven.
- **Fourteen consecutive losses** occurred inside 32 months. At a 28 % win rate that is
  the shape of it.
- Index CFDs are not the futures ICT taught on.

## The lock means: stop backtesting this

471 + 483 trades at PF ~1.1–1.2 is past the point where more backtesting decides
anything. **The next measurement is forward.**

Demo, log every signal whether or not you take it, and record for each one: timestamp,
instrument, side, entry, stop, target, planned R:R, fill price, exit price, exit reason,
and — the number that actually decides this — **the real all-in cost of the round trip**.
Track Arm A and Arm B separately. 100 trades.

Two things would break the lock and must be reported, not quietly absorbed:
- realised cost per round trip materially above 0.8 pip / 1.5 points, or
- **a run of losses beyond 21** (Arm A) / **19** (Arm B).

> **Corrected 2026-09-06.** This previously said "beyond 14", taken from the historical
> worst streak. A 20,000-path Monte Carlo on the actual R sequences puts the 95th
> percentile streak at **21 / 19** and the worst path at **37 / 38**. Stopping at 14
> would kill a working system on an ordinary bad run. The historical streak is a sample
> from the distribution, not its ceiling.

## Monte Carlo — what the path can actually look like

20,000 reshuffles of each book's real R sequence. Same edge, different order.

| book | actual DD | median DD | 5th-pct DD | worst DD | actual streak | 95th-pct streak | worst streak |
|---|---|---|---|---|---|---|---|
| Arm A live | −20.95 | −23.53 | **−37.24** | −64.72 | 12 | **21** | 37 |
| Arm B live | −15.94 | −19.82 | **−31.30** | −54.28 | 11 | **19** | 38 |
| Arm A holdout | −30.74 | −26.92 | −42.77 | −71.35 | 15 | 22 | 38 |
| Arm B holdout | −21.24 | −20.82 | −33.11 | −65.06 | 16 | 20 | 37 |

**The realised drawdown was better than the median path.** Plan for **−37 R**, not −21 R.
At 1 % risk per trade that is a −37 % account drawdown, so realistic sizing is
**0.25–0.5 %**. P(ending negative) is 0.000 across all four books — if the edge is real
the path can be ugly but the destination is not in doubt; that is the only thing a
reshuffle can tell you.

## Period stability — leave-one-year-out and walk-forward

US indices, 2015-2026, twelve years, rules frozen throughout.

**Arm A** full record n=571, PF **1.330**, +140.4 R. Ten of twelve years positive.

| removed year | PF without it | | removed year | PF without it |
|---|---|---|---|---|
| 2015 | 1.327 | | 2021 | 1.345 |
| 2016 | 1.417 | | 2022 | 1.349 |
| 2017 | 1.344 | | 2023 | 1.346 |
| 2018 | 1.273 | | 2024 | 1.326 |
| 2019 | 1.326 | | 2025 | **1.263** |
| 2020 | 1.332 | | 2026 | 1.306 |

`PF_without` never leaves **1.263 – 1.417**. No single year carries the record; the
largest share is 2025 at 29.1 %. Arm B is tighter still: eleven of twelve years positive,
`PF_without` range **1.419 – 1.572**.

Split at the lock boundary:

| | 2015-2023 (9 yr) | 2024-2026 (2.7 yr) |
|---|---|---|
| Arm A | PF **1.213**, +65.4 R, n=402 | PF **1.628**, +75.1 R, n=169 |
| Arm B | PF **1.457**, +112.2 R, n=319 | PF **1.657**, +66.6 R, n=139 |

The recent period is better, but the older nine years stand on their own. This is not a
recent-regime-only edge.

**Walk-forward**, rolling six-month windows, nothing re-optimised:

| | windows (n≥10) | PF > 1.0 | median window PF | worst window |
|---|---|---|---|---|
| Arm A | 23 | **19 (83 %)** | 1.234 | 2016-H2, PF 0.249, −15.9 R |
| Arm B | 21 | **17 (81 %)** | 1.312 | 2022-H2, PF 0.501, −12.4 R |

---

## Lock verification — the lock was tested, not just run

`python tests/verify_asia_lock.py` → **LOCK VERIFIED**

A pinned test that can never fail is worthless, so every locked knob was mutated one
step, in memory, and the pinned result checked for movement.

- **23 mutations, all 23 moved all 6 pinned fields.** No dead parameters; the pin
  covers every knob.
- baseline matches the pin before and after mutation (nothing left modified).
- `ASIA_LOCKED.md` values verified equal to `models/asia_locked.py`.

### The neighbourhood — 20 of 23 one-step neighbours are profitable

| mutation | n | PF | mutation | n | PF |
|---|---|---|---|---|---|
| swing n = 3 | 609 | 1.134 | entry = zone edge | 473 | 1.026 |
| swing n = 7 | 381 | 1.071 | stop buffer 1 unit | 492 | 1.173 |
| max_gap 30 | 455 | 1.169 | **target = fixed R** | 1546 | **0.944** |
| max_gap 60 | 463 | **1.195** | min_rr 1.5 | 643 | 1.110 |
| disp 0.4 | 495 | 1.152 | min_rr 3.0 | 252 | 1.132 |
| disp 0.7 | 385 | 1.099 | max_rr 8 | 457 | 1.187 |
| pools + PDH/PDL | 672 | 1.021 | max_rr 15 | 483 | 1.178 |
| **require_stl on** | 351 | **0.988** | cri_max 0.10 | 275 | **1.252** |
| require_bias on | 243 | 1.042 | cri_max 0.40 | 585 | 1.179 |
| **require_trend on** | 94 | **0.995** | window 240 min | 386 | **1.248** |
| killzone on | 284 | 1.191 | window 480 min | 517 | 1.119 |
| | | | max_hold 12 h | 472 | 1.144 |

The three that fall below 1.0 are exactly the ones the model already rejects: the
short-term-low discriminator, the trending-profile gate, and a fixed R target instead
of the draw on liquidity. **The edge lives in a region, not at a point.**

### Read this before touching anything

The locked config is **not the best point in its own neighbourhood.** `window_min = 240`
gives PF 1.248 on +72.7 R, and `cri_max = 0.10` gives PF 1.252 — both better than the
locked 1.189.

**Do not chase them.** The locked config is the one that was measured, held out and
pinned; those two are the top of a 23-point sweep looked at *after* the fact, and
picking them is exactly the re-search that killed six previous versions of this project.

More usefully, note the spread: one-step neighbours run from **0.944 to 1.252**. That
range is about the size of the claimed edge itself. It is the plainest available
statement of how much of the 1.189 is parameter noise — and the reason the next
measurement has to be forward, not another sweep.

---

## Target: fixed R vs dynamic — asked, measured, and DECIDED. Do not reopen.

**Decision 2026-09-06: the dynamic draw-on-liquidity target stays. The lock is
unchanged.** Recorded here with the full evidence so it is not re-litigated.

The question was whether a flat 3R (or any flat R) beats taking the pool. The naive
test — the `target="fixed"` mutation in the lock verification, PF 0.944 — is **not a
fair comparison**: switching to a fixed R also bypasses the `min_rr`/`max_rr` gate, so
it trades 1546 setups instead of 471. It answers "what if we dropped the gate too".

The clean test holds the setup population fixed (the same 471 trades, same DOL gate)
and moves only where the target sits. `models/target_study.py` and
`models/target_holdout.py`; raw output in `reports/target_study.txt`.

| exit | PF 2024-26 | totR | maxDD | streak | OOS PF | PF 2015-23 | rank new/old |
|---|---|---|---|---|---|---|---|
| **DYNAMIC pool (locked)** | 1.189 | +68.9 | −21.7 | **14** | 1.050 | 1.076 | 6 / 4 |
| flat 2.0R | 1.126 | +39.3 | −27.5 | 14 | 1.047 | 1.032 | 9 / 6 |
| flat 2.5R | 1.137 | +46.3 | −25.6 | 19 | 1.030 | 0.979 | 8 / 9 |
| flat 3.0R | 1.234 | +81.4 | −21.5 | 19 | 1.163 | 1.065 | 3 / 5 |
| flat 3.5R | 1.278 | +99.9 | −21.8 | 19 | 1.156 | 1.105 | 2 / 3 |
| **flat 4.0R** | **1.314** | **+115.5** | −24.2 | **23** | **1.190** | **1.149** | **1 / 1** |
| flat 5.0R | 1.168 | +65.6 | −42.9 | 23 | 0.998 | 1.133 | 7 / 2 |
| pool capped 4R | 1.224 | +79.1 | −22.1 | 14 | 1.115 | 1.019 | 4 / 8 |

**What the evidence actually says:** a flat 3.5–4R target beats the pool on both
periods. Flat 4R is rank 1 in *both* — 2024-2026 and the nine-year 2015-2023 holdout,
independent data. Rank agreement across the two periods is Spearman **+0.467**,
Pearson +0.583 (compare the MMXM's −0.26 / −0.66, which is what pure noise looks like).
Flat 2.5R dips in both periods, so the curve's shape replicates too.

**Why the lock did not change anyway.** The user's call, and it is defensible:

- The finding came from a 10-point sweep run *after* the lock. Rank agreement of +0.47
  is positive but far from 1.0 — some of the gap is still noise.
- Flat 4R costs a **23-trade losing streak** against 14, a deeper drawdown
  (−24.2 vs −21.7 recent, −46.5 vs −41.9 on the holdout), and a 26.4 % win rate.
- The DOL target is what the corpus specifies; the flat target is not.
- On **arm B (shorts) in the holdout the two are equal** — dynamic 1.200 vs flat 4R
  1.206 — so the case is weakest exactly where the strongest evidence of edge lives.

**One thing this study did establish, and it corrects the project record.**
`SETUP_FINAL.md` credits the draw-on-liquidity target as "the single largest
improvement in this project". Disentangled properly, that credit belongs to the
**R:R gate**, not to the target placement:

| | n | PF |
|---|---|---|
| fixed 2R, **no gate** | 1546 | 0.944 |
| fixed 2R, **with the gate** | 472 | 1.126 |
| flat 4R, with the gate | 470 | 1.314 |
| DOL pool, with the gate *(locked)* | 471 | 1.189 |

The gate is worth about +0.18 PF. Target placement is the weaker lever, and the pool is
not even the best placement. Keep the gate; that is the part that earns its keep.

**Status: closed.** Re-open only with forward data, not another sweep.
