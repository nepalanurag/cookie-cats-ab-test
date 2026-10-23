# Experiment plan: Cookie Cats progression gate, level 30 vs level 40

> **Honesty note.** This is a retrospective analysis of an experiment that
> Tactile Entertainment already ran and published as a dataset. This plan
> was written after the fact. It is **not** a pre-registration and claims
> no pre-registration: it documents the standards — metrics, guardrail,
> sizing, decision rule — that the analysis in this repo is held to, so a
> reader can check the analysis against them instead of trusting it.
> Where the completed experiment deviates from what this plan would have
> specified (sample split, available covariates), the decision memo says
> so and tests whether the deviation matters.

## Hypothesis

Moving the first progression gate from level 30 to level 40 delays the
first forced break. The design intuition is that players who are not
interrupted stay in flow longer and keep playing more over the following
week. The risk the hypothesis ignores: the gate may also function as a
pacing and difficulty-reset device, and removing it for ten more levels
could make the early game feel longer and flatter, reducing return visits.

Testable form: players assigned to gate_40 will have **higher day-7
retention** than players assigned to gate_30, with no significant loss in
engagement.

## Design

- Unit of randomization: player. Two arms, intended 50/50 split.
  - Control `gate_30`: gate at level 30 (the shipped design).
  - Treatment `gate_40`: gate at level 40.
- Realized sample: N = 90,189 (gate_30 n = 44,700; gate_40 n = 45,489).
  The split deviation is examined as a sample-ratio-mismatch (SRM) check
  in the decision memo, with sensitivity re-estimates.
- Observation window: retention at day 1 and day 7 after install;
  engagement over the first 14 days.

## Metrics

- **Primary: day-7 retention** (share of players who return on day 7).
  Day 7 is the horizon the hypothesis is actually about — sustained play,
  not first impressions — and it is the metric the ship decision turns on.
- **Secondary: day-1 retention.** Reported for direction and mechanism
  (an early-experience effect should appear here first), but it cannot
  carry a ship decision on its own.
- **Guardrail: engagement**, two components:
  - mean game rounds played in the first 14 days;
  - share of players who played 0 rounds.
  **Breach rule:** the guardrail is breached if gate_40 shows a
  statistically significant (alpha = 0.05) drop in mean rounds **or** a
  significant rise in the zero-round share. A breach blocks shipping even
  if a retention metric improves; a pass does not rescue a harmful
  primary result — it only rules out "players played less overall" as
  the explanation for a retention change.

## Sizing and minimum detectable effect

Baselines are the observed gate_30 rates (day-7 retention 19.02%,
day-1 retention 44.82%); all figures below are computed by
`src/analyze.py` and stored in `outputs/results.json`.

- At the realized ~45,000 players per arm, alpha = 0.05 two-sided,
  80% power, the minimum detectable effect is **0.73pp on day-7
  retention** and **0.93pp on day-1 retention**.
- Justification: this experiment exists to decide whether to change a
  core progression parameter for every future player. Effects below
  ~0.5pp on day-7 retention would be hard to distinguish from
  season-to-season drift and would rarely justify the change risk, so a
  design powered for ~0.7pp at this sample size is acceptable — but the
  limit must be stated, and it is: **this design cannot resolve effects
  smaller than about 0.73pp on the primary metric.** Detecting 0.5pp on
  day-7 retention at 80% power would require **97,679 players per arm**
  (195,358 total), roughly 2.2× this experiment's enrollment.
- Consequence for reading the result: a null on the primary metric from
  this design means "no effect of 0.73pp or larger," not "no effect."
  (As it happens, the primary result is not a null — see the memo.)

## Decision rule

Ship gate_40 only if **both** hold:

1. The day-7 retention difference is not significantly negative, and its
   95% CI rules out harm at the scale the design cares about (lower
   bound above −0.5pp).
2. The engagement guardrail does not breach.

A statistically significant day-7 harm is an automatic **no-ship**,
regardless of day-1 or engagement readings: the change has no measured
upside to trade against a proven loss on the primary metric. A
significant day-7 *gain* with a clean guardrail is a ship; anything in
between (null primary, clean guardrail) is a no-ship by default, because
gate_30 is the incumbent and the burden of proof is on the change.

Analysis standards: two-proportion z-tests with Wald 95% CIs on the
difference as the primary read; a bootstrap CI for the day-7 difference
as a robustness check; an SRM check on the realized split with
sensitivity re-estimates before any result is quoted.

## What this dataset cannot support

- **No subgroup claims.** The file ships no pre-treatment covariates
  (no acquisition channel, country, device, or pre-assignment behavior),
  so there is nothing valid to segment on. Any "works for segment X"
  claim from this data would be fabricated.
- **`sum_gamerounds` is a post-treatment variable.** Rounds are recorded
  over the 14 days *after* assignment, and the gate position itself can
  change how many rounds a player plays (a player the gate frustrates
  into churning records few rounds; a player in flow records many).
  Slicing the retention comparison by rounds played therefore conditions
  on a consequence of the treatment: within any rounds band, the two
  arms no longer contain comparable players, randomization is broken
  inside the slice, and the comparison can manufacture or erase effects
  (selection/collider bias). In this repo `sum_gamerounds` is used only
  **descriptively** — as the guardrail metric and as a rough balance
  signal — never as a segmentation variable for effect estimates.
- **No long-horizon readout.** Outcomes stop at day 7 (plus the 14-day
  engagement window). Nothing here speaks to day-30 retention or revenue.
