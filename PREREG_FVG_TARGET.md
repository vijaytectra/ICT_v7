# PRE-REGISTRATION — Stage A (FVG selection) and Stage B (day-scoped target unswept)

Frozen 2026-09-08, BEFORE any variant result was computed.  The power census below was
run first and is reported because it decides whether the experiment is worth running at
all; it uses no outcome information.

## Why these two and not others

The 59-combination barrier search (reports/barrier_combo.csv) covered exactly six axes:
entry position, target distance (rr_pool), direction, stop size in ATR, and bias
agreement.  It contains NO test of *which* FVG is chosen and NO test of whether the
target pool has already been taken today.  Both are therefore new search space rather
than a re-slice of the old.

## Power census (no outcome data used)

                          DEV indices _H 2015-23     VAL all nine 2024-26
  signals                        6,388                     4,903
  mean gaps per signal            2.21                      2.26
  exactly 1 gap                  44.7%                     41.8%
  2 gaps                         22.6%                     23.9%
  3 or more                      32.7%                     34.3%   (max 11)
  SELECTION CAN DIFFER           55.3%                     58.2%
  no fresh gap at all            17.6%                     17.1%

Selection has room to act on more than half the population, so Stage A is not vacuous.

## STAGE A — five FVG selection variants.  Detection unchanged.

  A0  FIRST         gaps[0]                                      <- baseline, locked model
  A1  LARGEST       max(hi - lo)
  A2  FRESH         first gap with  not mit_ce  and  not inverted
                    (if none exists the signal is DROPPED, ~17% of signals)
  A3  NEAREST_MSS   gap whose CE is closest in PRICE to the broken structure level
                    (`ref`) that the displacement closed through
  A4  NEAREST_RAID  gap whose CE is closest in PRICE to the raid extreme (sweep_px)

A3/A4 are read as PRICE distance, not bar distance: bar distance would collapse A4 into
A0 (gaps are emitted in bar order) and A3 into "last gap".

A2 is FROZEN as `not mit_ce and not inverted`.  Those are the corpus definitions
(fvg-mitigation.md: consumed at CE; inversion-fvg.md: polarity flips on a close beyond
the far edge), written before this data was examined.  The age / mitigated / mit_ce /
inverted breakdown is reported as a DESCRIPTIVE table and is NOT permitted to define a
variant in this pre-registration.

## STAGE B — two target rules only.

  B0  current rule                    pool must lie beyond entry; DOL reachability gate
  B1  + day-scoped unswept            drop any pool already taken TODAY

Day-scoped means: swept-state resets at every new calendar day; the Asian bounds are
monitored only from 09:00 EET (they are NaN before then in the detector, so a finite
ah/al always belongs to the same calendar date); PDH/PDL are monitored from 00:00.
Yesterday's touch of PDH does NOT count as swept.  A global `high[:signal_bar]` scan
would reject essentially every trade and collapse the sample - it is not tested.

Logged for description only, not used as filters in this pre-registration:
  target_wicked_today, target_closed_across_today, target_last_sweep_bar

## Metrics

  PRIMARY    p(+2R before -1R) on the real M1 path, from the actual fill and stop.
  SECONDARY  N, trades/week, WR, PF, expectancy R, avg win R, avg loss R,
             MAE R, MFE R, max drawdown R.

The primary metric is measured on the LOCKED population (min_rr 2.0, max_rr 10, CRI
0.20, DOL reachability, skip Monday).  That population is roughly a quarter of the one
used for reports/barrier_combo.csv, so these p-values are NOT comparable to the 33.33%
driftless base or the 50.0% PF-2 landmark in that table.  Read every A/B row as a delta
from A0/B0 in the same run.

## Slices

  DEV        indices only, 2015-2023          (selection set)
  VAL-IDX    indices only, 2024-2026          (same instruments, new time)
  VAL-FX     six FX majors, 2024-2026         (new instruments, new time)
  VAL        pooled, 2024-2026

VAL-IDX and VAL-FX are reported because the existing DEV/VAL split varies time AND
instrument at once, so "same direction in VAL" alone cannot separate the two.

## Acceptance criteria — frozen before the run

A candidate survives only if ALL hold:

  DEV      N >= 40   and  p(+2R) improves over A0/B0 by >= 3 percentage points
  VAL      N >= 25   and  p(+2R) improves over A0/B0 in the SAME DIRECTION
  both     PF does not fall below the A0/B0 baseline
  both     trades/week not below half the baseline

The highest DEV win rate does NOT win.  A variant with DEV 49% / VAL 34% on N=47 is
REJECTED; a variant with DEV 37% / VAL 37% on N=500 beats it.

## Multiple-testing budget, declared

Stage A 5 + Stage B 2 + Stage C 1 = 8 confirmatory hypotheses.  The 4 metadata axes are
descriptive and excluded.  Bonferroni at 8 puts a nominal 0.05 at 0.006.  This is on
top of 59 combinations and 29 single cuts already spent on this data.

## OOS

NOT TOUCHED in Stage A, B or C.  Reserved for a single final confirmation of at most one
surviving configuration.

## Harness control

The lab reproduces the pinned locked result (n=268, PF 1.538895) at A0+B0 before any
variant is read.  If it does not, no variant result is reported.
