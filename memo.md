# Decision memo: move the Cookie Cats progression gate from level 30 to level 40?

**Decision: DO NOT SHIP. Keep the gate at level 30.**

## Question

Tactile Entertainment tested moving the first progression gate in Cookie Cats
from level 30 to level 40, on the theory that a later forced break would keep
players engaged longer. Should gate_40 replace gate_30 for all players?

## Design

- Randomized controlled experiment, player-level assignment.
- Control `gate_30`: n = 44,700. Treatment `gate_40`: n = 45,489.
  Total N = 90,189 players (see `data/SOURCE.md` for provenance).
- Primary metrics, pre-declared: day-1 retention and day-7 retention.
- Guardrail metric, pre-declared: engagement, measured as mean game rounds
  played in the first 14 days and the share of players who played 0 rounds.
  **Guardrail rule:** the move breaches the guardrail if gate_40 shows a
  statistically significant (alpha = 0.05) drop in mean rounds or a
  significant rise in the zero-round share. A breach blocks shipping even if
  a primary metric improves; a pass does not rescue a harmful primary result,
  it only rules out "players played less overall" as the harm channel.
- Analysis: two-proportion z-tests with Wald 95% CIs on the difference,
  Welch's t-test and a proportion test for the guardrail, and a 10,000-draw
  bootstrap CI for the day-7 difference as a robustness check. Every number
  below is computed by `src/analyze.py` from the raw CSV and stored in
  `outputs/results.json`.

## Randomization check

- Split is 49.6% / 50.4%. A binomial test against 50/50 gives p = 0.009 —
  detectable at this sample size, but the imbalance is 789 players (0.9% of
  N), too small to manufacture a 0.8pp retention gap.
- Median rounds played: 17 (gate_30) vs 16 (gate_40), Mann-Whitney
  p = 0.050. The dataset ships no pre-treatment covariates, and rounds are
  recorded across the experiment window, so this is reported as a weak
  balance signal, not proof either way. Nothing here suggests broken
  randomization.

## Power

- At the realized sample sizes, the minimum detectable effect at 80% power
  and alpha = 0.05 is 0.93pp against the day-1 baseline rate (44.8%), and
  0.73pp against the day-7 control rate (19.0%).
- The observed day-7 difference (−0.82pp) is larger than the day-7 MDE, and
  the achieved power for an effect of that size is 0.89. **The test was
  powered for the day-7 difference it found** — this is not an underpowered
  null or a noise-level blip the study could not resolve.

## Results

| Metric | gate_30 | gate_40 | Diff (pp) | 95% CI (pp) | p |
|---|---|---|---|---|---|
| Day-1 retention | 44.82% | 44.23% | −0.59 | [−1.24, +0.06] | 0.074 |
| Day-7 retention | 19.02% | 18.20% | −0.82 | [−1.33, −0.31] | 0.002 |
| Mean rounds (guardrail) | 52.46 | 51.30 | −1.16 rounds | — | 0.376 |
| Zero-round share (guardrail) | 4.33% | 4.52% | +0.19 | [−0.08, +0.46] | 0.169 |

- Day-7 retention is **significantly worse** under gate_40: −0.82pp, a
  −4.3% relative drop. The bootstrap agrees with the parametric test:
  mean −0.82pp, 95% CI [−1.33, −0.32], and 99.9% of resamples fall below 0.
- Day-1 retention also points negative (−0.59pp) but is not significant
  (p = 0.074); its CI rules out any meaningful day-1 gain.
- Guardrail: **no breach.** Mean rounds and the zero-round share both move
  slightly in the harmful direction but neither is significant. Players did
  not play measurably less — they just came back less by day 7.

## Reasoning

The change has no measured upside anywhere: the primary long-horizon metric
(day-7 retention) is significantly worse, the short-horizon metric is flat to
negative, and the guardrail shows no compensating engagement gain. A
later gate does not make players play more; it appears to make them less
likely to still be playing a week later. When a variant is worse on the
metric that matters and better on nothing, there is nothing to trade off.

## Cost of a false positive

Shipping is the false-positive risk here: rolling out gate_40 if the day-7
effect is real costs **about 82 day-7 retained players per 10,000 new
installs** (95% CI: 31 to 133 per 10,000), compounding with every cohort,
and day-7 retained players are the pool future revenue comes from. The
opposite error — keeping gate_30 if gate_40 were truly neutral — costs
nothing measured: gate_40 showed no advantage on any metric, so there is no
upside being left on the table while we wait. The errors are asymmetric, and
both the point estimate and the asymmetry point the same way.

**Recommendation: do not ship gate_40. Keep the gate at level 30.** If the
team wants to revisit gate placement, test intermediate positions (e.g.
level 35) or pair the later gate with a difficulty/content change, powered
to detect 0.7pp on day-7 retention — roughly the sample size this test
already used.
