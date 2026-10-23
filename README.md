# Cookie Cats A/B test: should the gate move from level 30 to level 40?

**Decision: DO NOT SHIP. Keep the gate at level 30.** Moving the gate to
level 40 significantly reduces day-7 retention (−0.82pp, p = 0.002) with
no measured upside on any metric — and the verdict survives an SRM
investigation of the uneven arm split and two sensitivity re-estimates.
Full reasoning: [`docs/decision_memo.md`](docs/decision_memo.md);
standards the analysis is held to:
[`docs/experiment_plan.md`](docs/experiment_plan.md).

A complete, reproducible analysis of a real randomized A/B test run by
Tactile Entertainment on the mobile game Cookie Cats: 90,189 players
randomly assigned to the progression gate at level 30 (control, n = 44,700)
or level 40 (treatment, n = 45,489). Includes a power analysis, an
engagement guardrail with a pre-declared breach rule, a bootstrap
robustness check, an SRM (sample-ratio-mismatch) check with
reweighting/trimming sensitivity analyses, and a sized follow-up
experiment design.

## Headline results (computed by `src/analyze.py`, stored in `outputs/results.json`)

- **Day-1 retention:** 44.82% vs 44.23% — difference −0.59pp,
  95% CI [−1.24, +0.06], p = 0.074 (not significant).
- **Day-7 retention:** 19.02% vs 18.20% — difference **−0.82pp**,
  95% CI [−1.33, −0.31], p = 0.002 (−4.3% relative). Bootstrap 95% CI
  [−1.33, −0.32]; 99.9% of resamples below zero.
- **Power:** minimum detectable effect at 80% power is 0.93pp against the
  day-1 baseline and 0.73pp against the day-7 baseline; achieved power for
  the observed day-7 effect is 0.89, so the test was powered for the
  difference it found.
- **Guardrail (engagement):** mean rounds 52.46 vs 51.30 (p = 0.376);
  zero-round share 4.33% vs 4.52% (p = 0.169). No breach.
- **SRM check:** the realized split is 49.56% / 50.44%, not 50/50.
  Chi-square SRM test: χ² = 6.90, p = 0.0086 — trips the p < 0.01
  "investigate" threshold, not the p < 0.001 hard-alarm threshold.
- **Sensitivity:** reweighting both arms to 50/50 (inverse-probability
  weights) leaves the day-7 difference at −0.82pp [−1.33, −0.31]; 1,000
  random trims of gate_40 to an exact 44,700/44,700 split give a mean
  difference of −0.82pp, significant in 100% of trims. **The conclusion
  does not depend on the split imbalance.**
- **Follow-up sizing:** detecting a 0.5pp day-7 effect at 80% power
  needs 97,679 players per arm (195,358 total) — the memo's proposed
  gate_35 test is budgeted at that size.

## Run it

```bash
pip install -r requirements.txt
python3 src/analyze.py
```

The script verifies the dataset (columns, unique userids, both arms),
prints a run log, and writes `outputs/results.json` plus four figures to
`figures/` (retention by arm, engagement distribution, bootstrap
distribution of the day-7 difference, retention decay curve). The output
of the verified run is saved in `RUN_LOG.txt`. CI (`.github/workflows/`)
re-runs the script on every push and fails if the regenerated
`outputs/results.json` differs from the committed one — which is why
`requirements.txt` is fully pinned: the last digits of a few p-values
move between scipy builds, and the check is byte-exact.

## Layout

- `data/cookie_cats.csv` — player-level experiment data; `data/SOURCE.md`
  documents provenance (Kaggle dataset via a public GitHub mirror, with
  hash and verification counts).
- `src/analyze.py` — the full analysis, nothing else computes numbers.
- `outputs/results.json` — every statistic cited in the memo and README.
- `docs/experiment_plan.md` — hypothesis, metrics, guardrail rule,
  sizing, decision rule (written retrospectively; it documents the
  standards applied, and says so).
- `docs/decision_memo.md` — the ship/no-ship decision memo.
- `memo.md` — pointer to the decision memo (kept for old links).

## Resume bullet

> Analyzed a 90,189-player randomized A/B test of a progression-gate change
> with power analysis, two-proportion z-tests, a pre-declared engagement
> guardrail, and bootstrap CIs; found the change cut day-7 retention by
> 0.82pp (95% CI −1.33 to −0.31, p = 0.002) with no engagement gain, and
> recommended against shipping it.
