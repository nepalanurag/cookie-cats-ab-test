# Cookie Cats A/B test: should the gate move from level 30 to level 40?

A complete, reproducible analysis of a real randomized A/B test run by
Tactile Entertainment on the mobile game Cookie Cats: 90,189 players
randomly assigned to the progression gate at level 30 (control, n = 44,700)
or level 40 (treatment, n = 45,489). Includes a randomization check, a power
analysis, pre-declared primary and guardrail metrics, a bootstrap
robustness check, and a ship/no-ship decision memo (`memo.md`).

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
- **Decision: do not ship.** Moving the gate to level 40 significantly
  reduces day-7 retention with no measured upside — roughly 82 fewer day-7
  retained players per 10,000 installs if the effect is real.

## Run it

```bash
pip install -r requirements.txt
python3 src/analyze.py
```

The script verifies the dataset (columns, unique userids, both arms),
prints a run log, and writes `outputs/results.json` plus three figures to
`figures/` (retention by arm, engagement distribution, bootstrap
distribution of the day-7 difference). The output of the verified run is
saved in `RUN_LOG.txt`.

## Layout

- `data/cookie_cats.csv` — player-level experiment data; `data/SOURCE.md`
  documents provenance (Kaggle dataset via a public GitHub mirror, with
  hash and verification counts).
- `src/analyze.py` — the full analysis, nothing else computes numbers.
- `outputs/results.json` — every statistic cited in the memo and README.
- `memo.md` — the ship/no-ship decision memo.

## Resume bullet

> Analyzed a 90,189-player randomized A/B test of a progression-gate change
> with power analysis, two-proportion z-tests, a pre-declared engagement
> guardrail, and bootstrap CIs; found the change cut day-7 retention by
> 0.82pp (95% CI −1.33 to −0.31, p = 0.002) with no engagement gain, and
> recommended against shipping it.
