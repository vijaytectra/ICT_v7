# STAGE A / STAGE B RESULT — FVG selection and day-scoped target unswept

Contract frozen in PREREG_FVG_TARGET.md before any number below was read.
Harness control: the lab reproduces the pinned locked result exactly, n=268, PF=1.538895.
Lock re-verified after the additive `ref` field: all six pinned tests pass.

## Headline

**Nothing survives.**  Four of five FVG variants are rejected outright.  Stage B is
rejected in the wrong direction and also fails the frequency floor.  The one variant
that passes the letter of the contract passes it on noise, because of a flaw in the
contract I wrote — see "The threshold was wrong" below.

## Stage A — five FVG selection rules

Primary metric p(+2R before -1R) on the locked population.  A0 FIRST is the baseline:
DEV 41.03% (n=368), VAL 42.16% (n=268).  These are NOT comparable to the 33.33% base in
reports/barrier_combo.csv, which used a population ~4x larger with no min_rr/DOL gates.

    variant         d p2R DEV   d p2R VAL    z DEV   p DEV    z VAL   p VAL   freq   verdict
    LARGEST            +0.41       +2.42      0.11   0.913     0.55   0.583   0.83   REJECT
    FRESH              +3.07       +0.40      0.77   0.441     0.09   0.931   0.71   pass*
    NEAREST_MSS        -3.69       -2.57     -0.91   0.365    -0.56   0.577   0.63   REJECT
    NEAREST_RAID       +0.08       +0.34      0.02   0.982     0.08   0.937   1.02   REJECT

Full metrics, four slices, in reports/stage_ab/summary.csv.

## The threshold was wrong, and FRESH exposes it

The contract required "DEV improves by >= 3 percentage points".  It did not require that
improvement to be distinguishable from zero.  FRESH cleared the bar by 0.07pp:

    DEV   diff +3.07pp   95% CI [-4.75, +10.95]pp   P(diff <= 0) = 0.224
    VAL   diff +0.40pp   95% CI [ -8.65,  +9.45]pp   P(diff <= 0) = 0.466

and it does not replicate on new instruments:

    VAL-IDX   FRESH 45.31% (n=128)  vs  FIRST 44.63% (n=177)   +0.68pp
    VAL-FX    FRESH 37.31% (n= 67)  vs  FIRST 37.36% (n= 91)   -0.05pp

A 3pp threshold on n~300 is inside one standard error.  Any of the five variants could
have cleared it by chance; FRESH is the one that did.  The threshold should have been
"improves by >= 3pp AND the bootstrap CI excludes zero".  Recorded so the next
pre-registration does not repeat it.

FRESH is REJECTED on the substance.  Stage C is therefore not run: promoting FRESH would
be exactly the "one more good-looking backtest" this contract exists to prevent.

## Stage B — day-scoped target unswept

    B0  current rule       DEV 41.03% p2R, PF 1.52, 0.78/wk   VAL 42.16%, PF 1.54, 1.92/wk
    B1  + unswept          DEV 38.82% p2R, PF 1.47, 0.32/wk   VAL 41.44%, PF 1.41, 0.80/wk

Rejected on four counts: DEV moves -2.22pp (wrong direction), VAL -0.72pp (wrong
direction), PF falls in both periods, and trade frequency collapses to 0.41x the
baseline — below the pre-registered half-baseline floor.

### The sign is backwards from doctrine, and there is a mechanism

The filter bites hard: 60.3% (DEV) / 59.0% (VAL) of baseline trades were already
targeting a pool that today's price had wicked.  Splitting the baseline on it:

                already swept today          not swept today
    DEV         42.34%  n=222  PF 1.57       39.04%  n=146  PF 1.46
    VAL         43.04%  n=158  PF 1.62       40.91%  n=110  PF 1.43
    POOLED      42.63%  n=380                39.84%  n=256   diff +2.79pp  z=+0.70  p=0.483

Consistent sign in both periods, but p=0.48 — not significant, and not claimed as a
result.  What matters is the direction, because it has a mechanism rather than being a
free-floating correlation:

  DOL reachability, the ONE filter in this project that passed a permutation test
  (p=0.0002 DEV / 0.0000 VAL), requires the target to have been CROSSED ON A CLOSE at
  least twice in the last 96 structure bars.  "Already swept today" is a stronger form
  of the same property: price has demonstrably been able to reach that level, today.

So B1 removes precisely the trades the one working filter selects for.  That explains
both the wrong sign and the 59% frequency collapse.  ICT doctrine says target an unswept
pool; on this model, measured, reachability beats freshness.  This does not overturn the
doctrine on the evidence available — it says the doctrinal filter is redundant with, and
opposed to, a filter that is already in the locked config and already validated.

## Descriptive only — properties of the selected gap (A0)

Not permitted to define a variant here.  Recorded for a future pre-registration.

    cut               n DEV   n VAL   p2R DEV   p2R VAL   PF DEV   PF VAL
    age <= 2            106      86     43.40     48.84     1.44     2.17
    age 3-5              78      60     37.18     40.00     1.60     0.94
    age >= 6            184     122     41.30     38.52     1.54     1.48
    mitigated           200     128     40.50     43.75     1.59     1.56
    not mitigated       168     140     41.67     40.71     1.44     1.52
    mit at CE           165     109     38.79     42.20     1.43     1.47
    not mit at CE       203     159     42.86     42.14     1.60     1.59
    inverted             94      55     37.23     45.45     1.37     1.60
    not inverted        274     213     42.34     41.31     1.58     1.52
    1 gap only          124     107     40.32     40.19     1.61     1.27
    2+ gaps             244     161     41.39     43.48     1.48     1.73

Note `age <= 2` reads best in both periods (+2.4pp DEV, +6.7pp VAL) — the OPPOSITE of
the corpus rule that an FVG rebalanced within 1-3 bars is "a reading signal, NOT entry"
and a 5+ bar gap is "the one you plan and wait for".  That is a hypothesis for a fresh
pre-registration with its own DEV/VAL, not something to fold into this one.

## What 6 trades in a week actually looks like

Exact binomial on the measured win rate, no partials, no break-even.

    config                    WR%   E[wins]/6   P(>=4 of 6)   P(>=3 of 6)   P(0 of 6)
    A0 FIRST  DEV           32.34        1.94         0.091         0.300       0.096
    A0 FIRST  VAL           33.58        2.01         0.103         0.325       0.086
    hypothetical WR 45%     45.00        2.70         0.255         0.558       0.028
    hypothetical WR 60%     60.00        3.60         0.544         0.821       0.004
    target    WR 70%        70.00        4.20         0.744         0.930       0.001

At the measured win rate, a 6-trade week produces 4 or more wins about **one week in
ten**, and zero wins about **one week in eleven**.  The system is profitable at PF ~1.54
because the average win is 3.3R against a 1.09R average loss — not because most weeks
look like winning weeks.  Any expectation built on "4 of 6" needs a win rate this signal
family has not produced under any of the 59 combinations or the 5 variants tested here.

## POWER — added after the run, and it limits what this result may be used to claim

The primary metric was a BINARY (did the +2R barrier fall before the -1R barrier).  A
binary discards the payoff information that constitutes this system's edge: the average
win is 3.3R against a 1.09R average loss, and the barrier metric cannot see that.

Minimum detectable effect at 80% power, alpha 0.05 two-sided:

    DEV  variant vs A0        n=368/368    +10.2pp
    VAL  variant vs A0        n=268/268    +11.9pp
    DEV  60% subset vs rest   n=220/147    +14.7pp

    n per arm needed to detect +3pp : 4,215
    n per arm needed to detect +5pp : 1,518

For calibration: the largest single-filter lift ever measured in this project is +6.2pp
(entry_pos <= 0.15), and the DOL reachability gate - the one feature that passed a
permutation test - lifts the win rate 27.4% -> 32.8%, which is +5.4pp.

**Both are below this study's detection floor.**  So "nothing survives" is the correct
DECISION, but the correct INFERENCE is narrower than it looks:

  * SUPPORTED: no FVG selection rule tested here produces an effect large enough to act
    on, and none comes near the +16.7pp that PF 2.0 would require.
  * NOT SUPPORTED: "FVG selection does not matter."  An effect of +3 to +6pp - the size
    of every real effect this project has ever found - would have been invisible to this
    design.  It was not measured absent; it was not measurable.

The same limit applies to Stage B.  B1 moving -2.2pp / -0.7pp is consistent with a small
negative effect AND with no effect; what makes the rejection safe is not the size but
the frequency collapse to 0.41x and the PF fall in both periods.

### Why DOL reachability WAS detectable and this was not: the metric, not the effect

Random same-size subsets (62% of trades, 20,000 draws) give the null spread of each
metric:

                       binary p2R          expectancy R
    DEV   SD of diff      2.00pp              0.094R
    VAL   SD of diff      2.38pp              0.107R

DOL's measured expectancy lift on DEV is 0.414R filtered against 0.178R unfiltered,
i.e. **+0.236R**, against a 1.96-SD threshold of 0.184R.  Detectable.  The same feature
expressed as a binary proportion would have sat at roughly half its detection floor.

Conclusion for any future stage: use EXPECTANCY with a permutation test against random
same-size subsets - the test that actually found DOL - and keep p(+2R) as a descriptive
secondary.  The binary was the right instrument for "can any selection reach the 50%
that PF 2.0 needs" and the wrong instrument for "does this feature select".

## Budget spent

8 confirmatory hypotheses declared, 6 used (5 Stage A + 1 Stage B).  Stage C not run.
OOS untouched.  Running total on this data: 29 single cuts + 59 combinations + 6 here.
