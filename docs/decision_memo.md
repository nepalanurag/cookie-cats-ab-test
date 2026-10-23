# Decision memo: move the Cookie Cats progression gate from level 30 to level 40?

**Recommendation: DO NOT SHIP. Keep the gate at level 30.**

The experiment plan this analysis is held to — metrics, guardrail,
sizing, decision rule — is in
[`docs/experiment_plan.md`](experiment_plan.md). Every number below is
computed by `src/analyze.py` from the raw data and stored in
`outputs/results.json`.

## Context

Tactile Entertainment randomized 90,189 Cookie Cats players to the first
progression gate at level 30 (control, n = 44,700) or level 40
(treatment, n = 45,489). The bet behind gate_40: a later forced break
keeps players in flow longer and improves retention. This memo decides
whether gate_40 should replace gate_30 for all players.

## Evidence

| Metric | gate_30 | gate_40 | Diff | 95% CI | p |
|---|---|---|---|---|---|
| **Day-7 retention (primary)** | 19.02% | 18.20% | **−0.82pp** | [−1.33, −0.31] | 0.002 |
| Day-1 retention (secondary) | 44.82% | 44.23% | −0.59pp | [−1.24, +0.06] | 0.074 |
| Mean rounds, 14d (guardrail) | 52.46 | 51.30 | −1.16 | — | 0.376 |
| Zero-round share (guardrail) | 4.33% | 4.52% | +0.19pp | [−0.08, +0.46] | 0.169 |

- **The primary metric is significantly worse under gate_40:** day-7
  retention falls 0.82pp, a −4.3% relative drop. The bootstrap agrees
  with the parametric test (95% CI [−1.33, −0.32]; 99.9% of resamples
  below zero).
- **The result is not a power artifact.** The design's minimum
  detectable effect on day-7 retention is 0.73pp; the observed −0.82pp
  exceeds it, with achieved power 0.89.
- **The decay view points the same way.** Day-1 returners who are still
  playing at day 7: 33.3% under gate_30 vs 32.3% under gate_40
  (`figures/retention_curve.png`). The gap is not an install-day blip; it
  widens slightly across the week.
- **Guardrail: no breach.** Neither engagement component moves
  significantly. Players did not play measurably less — they came back
  less. That also kills the friendliest explanation for shipping ("they
  play more per session, so it evens out"): there is no session gain to
  even anything out.

## The split is uneven — and the verdict survives it

The realized split is 49.56% / 50.44% instead of 50/50. We checked this
the way an experimentation platform would, and then stress-tested the
conclusion against it:

- **SRM check.** Chi-square goodness-of-fit against the designed 50/50
  split: χ² = 6.90, **p = 0.0086** (`srm` in `outputs/results.json`). That
  trips the lenient p < 0.01 "investigate" threshold but not the
  p < 0.001 hard-alarm threshold platforms typically page on. The
  imbalance is 789 players, 0.87% of N — worth investigating, and small
  next to a 0.82pp effect.
- **Sensitivity 1 — reweighting.** Re-estimating with
  inverse-probability weights (w = 0.5 / arm share: 1.0088 for gate_30,
  0.9913 for gate_40) gives day-7 diff **−0.82pp, 95% CI [−1.33, −0.31]**
  — unchanged, as it must be: weights constant within an arm cannot move
  an arm mean. The check confirms the result is not a pooling artifact.
- **Sensitivity 2 — trimming.** Re-running the test 1,000 times with
  gate_40 randomly trimmed to exactly 44,700 players (a true 50/50
  design): mean diff **−0.82pp**, 95% of trims land in [−0.87, −0.78]pp,
  and **100% of trims are significant at alpha = 0.05** with the same
  sign. The conclusion does not depend on the 789 excess treatment
  players.

Residual concern, stated plainly: the dataset ships no pre-treatment
covariates, so we cannot verify *why* the split drifted or check balance
on player characteristics. That is a reason to fix instrumentation
before the next test (below), not a reason to discount a result that
survives both sensitivity checks.

## Risks

- **If we ship and the effect is real** (the reading the evidence
  supports): roughly **82 fewer day-7 retained players per 10,000
  installs** (95% CI: 31 to 133), compounding across every future
  cohort. Day-7 retained players are the pool all later revenue comes
  from.
- **If we do not ship and gate_40 is secretly neutral:** we lose
  nothing measured. Gate_40 showed no advantage on any metric, so no
  upside is being deferred; gate_30 stays available to beat in a better
  test.
- **Measurement risk:** outcomes stop at day 7 (engagement at day 14).
  We cannot see day-30 retention or revenue from this data, in either
  direction.
- **Transport risk:** this is one game, one gate, one era of the player
  base. The finding is a decision input for Cookie Cats' gate, not a
  law about progression design.

The asymmetry is the decision: one error costs a compounding retention
loss, the other costs nothing we can measure.

## What would change this call

- A re-run with a verified-clean split whose day-7 CI excludes harm
  beyond 0.5pp — i.e., evidence the loss was an artifact of this
  experiment's assignment, at a sample size that can actually resolve
  0.5pp (see follow-up sizing).
- Longer-window data (day-14/day-30 retention) showing gate_40 players
  recover and overtake after day 7.
- A version of the treatment that changes more than the gate position —
  e.g., gate_40 paired with a difficulty/content rebalance of levels
  31–40 — testing positive on day-7 retention. That would be a different
  treatment, and it would earn its own ship decision.
- Instrumented pre-treatment covariates revealing a definable player
  segment that gains under a later gate, large enough to target. (This
  dataset cannot produce that evidence; see the plan's note on
  post-treatment variables.)

## Follow-up experiment

If the team wants to keep exploring gate placement, test the middle
position instead of re-litigating 40:

- **Arms:** gate_30 (control, incumbent) vs gate_35. Optional third arm:
  gate_40 with a difficulty rebalance of levels 31–40, if design can
  ship it — it tests the "gate plus pacing" hypothesis rather than gate
  position alone.
- **Primary metric:** day-7 retention, same definitions and guardrail
  as this plan.
- **Sizing:** to detect **0.5pp** on day-7 retention at 80% power,
  alpha = 0.05, from the 19.02% baseline: **97,679 players per arm
  (195,358 total)** — about 2.2× this experiment's enrollment
  (`followup_sample_size` in `outputs/results.json`). Budget the runtime
  from live install traffic; do not repeat this test's mistake of
  reading a design at its MDE limit as if it were precise.
- **Before launch:** log pre-treatment covariates (install source,
  country, device class) and add an automated SRM alarm at p < 0.001, so
  the next split question is answered by data instead of sensitivity
  analysis.

## Bottom line

Gate_40 loses 0.82pp of day-7 retention, gains nothing on engagement,
and the loss survives an SRM investigation and two sensitivity
re-estimates. There is nothing to trade off. **Keep the gate at 30**;
if gate placement is revisited, test level 35 at the sample size above.
