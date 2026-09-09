# Detector change tested: `reclaim` trigger + London-killzone raid

The one part of the locked model never varied was the **detector**. Its unexamined
assumption is how the reversal is confirmed: a close through the **swing high current at
the raid** — a full market-structure shift. That swing can sit far above the raid low, so
the trigger fires late, which is the exact shape of the two biggest failure modes in
`LOSS_FORENSICS.md` (33 % of losses never move; 634 signals never fill).

Two sourced changes, both previously untested:

1. **`reclaim` trigger** — confirmation is price closing back through the raided Asian
   bound itself. `market-maker-trap.md` variant 2: a break below consolidation that
   reverses *is* the accumulation event. `liquidity-sweep.md`: "close to it without
   sustaining the break."
2. **raid must occur in the London killzone, 09:00–12:00 EET.** The Asian range is the
   accumulation for the *London* manipulation (`intraday-amd.md`: M = 02:00–05:00 NY).
   The locked model accepts a raid at any hour after 09:00, including 20:00 EET.

`models/asia_v3.py`. `trigger='mss'` reproduces the lock exactly on both periods
(402 / 1.2132 / +65.365 and 395 / 1.2940 / +87.932) — verified before anything else was
read.

## Selection: US indices 2015-2023 only (9 years)

| arm | n | /month | PF | totR | P(edge) | CI low |
|---|---|---|---|---|---|---|
| mss (LOCKED) | 402 | 3.7 | 1.213 | +65.4 | 0.941 | −0.038 |
| cisd | 674 | 6.2 | 1.064 | +34.2 | 0.735 | −0.102 |
| cisd + mss | 367 | 3.4 | 1.182 | +51.0 | 0.900 | −0.073 |
| reclaim | 1149 | 10.6 | 1.114 | +104.3 | 0.925 | −0.031 |
| mss raid 09-12 | 279 | 2.6 | 1.103 | +22.9 | 0.742 | −0.155 |
| cisd raid 09-12 | 443 | 4.1 | 1.218 | +75.9 | 0.954 | −0.028 |
| **reclaim raid 09-12** | **570** | **5.3** | **1.244** | **+110.1** | **0.981** | **+0.010** |

## Validation — applied UNCHANGED

### ARM A (both sides): REJECTED

| slice | locked | reclaim+LDN |
|---|---|---|
| indices DEV 2015-23 *(selected here)* | 1.213 · +65.4 | **1.244 · +110.1** |
| indices VAL 2024-26 | **1.628 · +75.1** | 1.191 · +36.1 |
| FX VAL 2024-26 | **1.072 · +12.9** | **0.979 · −7.9** |
| all 9 VAL 2024-26 | **1.294 · +87.9** | 1.050 · +28.3 |

Wins only where it was selected; loses on the other period and on the other market.
This is the LR3 signature. Rejected for Arm A.

### ARM B (shorts only): survives every slice on total R

| slice | locked n/PF/totR/DD | reclaim+LDN n/PF/totR/DD |
|---|---|---|
| indices DEV 15-23 | 227 · 1.476 · +78.7 · −14.5 | 319 · 1.457 · **+112.2** · −21.2 |
| indices VAL 24-26 | 94 · **1.813** · +52.3 · −7.8 | 139 · 1.657 · **+66.6** · −11.3 |
| FX VAL 24-26 | 118 · **1.552** · +46.3 · −9.9 | 243 · 1.357 · **+64.6** · −12.3 |
| all 9 VAL 24-26 | 212 · **1.665** · +98.6 · −14.5 | 382 · 1.465 · **+131.2** · −15.9 |

Total R is higher in **all four** slices. Profit factor is lower in all four. Trade count
roughly doubles. R per R of drawdown: DEV indices 5.44→5.28, VAL indices 6.74→5.90,
VAL FX 4.66→**5.27**, VAL all-9 6.78→**8.23**.

Per instrument, shorts, 2024-2026 — **8 of 9 positive**:

| sym | locked n/PF/totR | reclaim+LDN n/PF/totR |
|---|---|---|
| USATECH | 38 · 1.727 · +20.3 | 63 · 1.588 · **+28.8** |
| USA30 | 47 · 2.040 · +30.8 | 64 · 1.587 · +26.8 |
| USA500 | 9 · 1.170 · +1.2 | 12 · 2.621 · **+11.0** |
| EURUSD | 16 · 1.506 · +5.7 | 34 · 1.909 · **+20.3** |
| USDCAD | 19 · 1.214 · +3.1 | 39 · 1.909 · **+22.6** |
| AUDUSD | 19 · 1.735 · +9.3 | 38 · 1.565 · **+15.0** |
| USDJPY | 25 · 1.136 · +3.0 | 51 · 1.264 · **+10.8** |
| USDCHF | 16 · 2.991 · +13.7 | 32 · 1.330 · +7.5 |
| **GBPUSD** | 23 · 1.686 · +11.5 | 49 · **0.735** · **−11.5** |

Per year on the dev market, both versions are positive in 8 of 9 years.

## Why Arm A fails and Arm B does not

Longs are the losing side — PF 0.906 and −32.6 R across 11.7 years. A looser trigger adds
trades on both sides, so on Arm A it adds mostly junk and dilutes. On shorts it widens the
side that actually has edge. The asymmetry is not a coincidence; it is the same
short/long split already documented in `ASIA_MODEL_REPORT.md`.

## The decision this poses

More trades and more total R, at a lower profit factor and a slightly deeper drawdown.
For fixed-fractional sizing, total R per unit of drawdown is what compounds, and that is
better on the pooled validation set (8.23 vs 6.78) and about level on the dev set. For a
profit-factor criterion, the locked version wins.

GBPUSD flips from +11.5 R to −11.5 R and is the one genuine failure. Dropping it after
the fact would be instrument cherry-picking and has not been done.

Code: `models/asia_v3.py`, `models/v3lab.py`, `models/run_v3_dev.py`,
`models/run_v3_val.py`, `models/run_v3_shorts.py`.
Data: `reports/v3_dev.csv`, `reports/v3_val.csv`, `reports/v3_shorts.csv`.
