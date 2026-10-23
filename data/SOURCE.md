# Data source

`cookie_cats.csv` — player-level data from Tactile Entertainment's Cookie Cats
mobile game A/B test (gate moved from level 30 to level 40). The dataset is
distributed on Kaggle ("Mobile Game Retention Analysis A/B testing",
kaggle.com/jyunyolin), which requires authentication, so the file here was
taken from a public GitHub mirror of the same dataset:

- Downloaded from:
  https://raw.githubusercontent.com/ryanschaub/Mobile-Games-A-B-Testing-with-Cookie-Cats/master/cookie_cats.csv
- File size: 2,707,297 bytes
- MD5: 99b48ea3d4a552fa6b27aac60a8cfddf
- Cross-checked against a second, independently serialized mirror
  (ghaskari/cookie-cats-ab-test): identical row count, group sizes and values.

## Verification (run 2026-10-22, pandas read of the file itself)

- Rows: 90,189 players. NOTE: the audit spec that commissioned this project
  said 90,118; two independent mirrors both contain 90,189 rows with
  identical group splits, so 90,118 appears to be a digit transposition.
  Every number in this project is computed from the 90,189-row file above.
- Columns: `userid` (unique per row), `version` (gate_30 / gate_40),
  `sum_gamerounds` (rounds played in the first 14 days), `retention_1`,
  `retention_7` (booleans).
- Group sizes: gate_30 = 44,700 users; gate_40 = 45,489 users.
- No duplicate userids.
