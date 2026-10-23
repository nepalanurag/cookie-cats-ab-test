"""Cookie Cats gate_30 vs gate_40 A/B test analysis.

Computes every number from data/cookie_cats.csv and writes:
  outputs/results.json, figures/*.png.
Run: python3 src/analyze.py   (from the project root)
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportions_ztest,
)

ROOT = Path(__file__).resolve().parent.parent
SEED = 42
ALPHA = 0.05

df = pd.read_csv(ROOT / "data" / "cookie_cats.csv")

# --- runnable check: the dataset is what we claim it is -------------------
assert list(df.columns) == ["userid", "version", "sum_gamerounds",
                            "retention_1", "retention_7"], df.columns
assert df["userid"].is_unique
assert set(df["version"]) == {"gate_30", "gate_40"}
g30 = df[df.version == "gate_30"]
g40 = df[df.version == "gate_40"]
print(f"rows={len(df)}  gate_30={len(g30)}  gate_40={len(g40)}")

R = {"n_total": int(len(df)),
     "n_gate_30": int(len(g30)), "n_gate_40": int(len(g40))}

# --- randomization check ----------------------------------------------------
# Split vs 50/50 (binomial) and the engagement distribution, which is
# recorded over the same window for both arms; a broken randomization
# would show up here as a lopsided split.
binom_p = stats.binomtest(len(g30), len(df), 0.5).pvalue
mw = stats.mannwhitneyu(g30.sum_gamerounds, g40.sum_gamerounds,
                        alternative="two-sided")
R["randomization"] = {
    "split_binomial_p": float(binom_p),
    "gamerounds_median_gate_30": float(g30.sum_gamerounds.median()),
    "gamerounds_median_gate_40": float(g40.sum_gamerounds.median()),
    "gamerounds_mannwhitney_p": float(mw.pvalue),
}
print(f"randomization: split binomial p={binom_p:.3f}; "
      f"median rounds 30={g30.sum_gamerounds.median()} "
      f"40={g40.sum_gamerounds.median()}; MWU p={mw.pvalue:.3f}")


def prop_test(ctrl: pd.Series, treat: pd.Series) -> dict:
    """Two-proportion z-test, treat - ctrl, with Wald 95% CI on the diff."""
    nc, nt = len(ctrl), len(treat)
    xc, xt = int(ctrl.sum()), int(treat.sum())
    pc, pt = xc / nc, xt / nt
    z, p = proportions_ztest([xt, xc], [nt, nc])
    lo, hi = confint_proportions_2indep(xt, nt, xc, nc, method="wald")
    return {
        "rate_gate_30": pc, "rate_gate_40": pt,
        "diff_pp": (pt - pc) * 100,
        "ci95_pp": [lo * 100, hi * 100],
        "relative_change_pct": (pt - pc) / pc * 100,
        "z": float(z), "p_value": float(p),
    }


# --- primary metrics ---------------------------------------------------------
R["retention_1"] = prop_test(g30.retention_1, g40.retention_1)
R["retention_7"] = prop_test(g30.retention_7, g40.retention_7)
for k in ("retention_1", "retention_7"):
    r = R[k]
    print(f"{k}: gate_30={r['rate_gate_30']:.4f} gate_40={r['rate_gate_40']:.4f} "
          f"diff={r['diff_pp']:+.2f}pp CI[{r['ci95_pp'][0]:+.2f},{r['ci95_pp'][1]:+.2f}] "
          f"p={r['p_value']:.4g}")

# --- power analysis ---------------------------------------------------------
# MDE at 80% power, alpha=0.05 two-sided, from the realized per-arm sample
# sizes. Computed at two planning baselines: the D1 retention rate (the
# headline metric a planner would power on) and the D7 control rate (the
# relevant baseline for judging whether the D7 comparison itself was
# powered for the difference it found).
za = stats.norm.ppf(1 - ALPHA / 2)
zb = stats.norm.ppf(0.80)


def mde_pp(p_base: float) -> float:
    se = np.sqrt(p_base * (1 - p_base) * (1 / len(g30) + 1 / len(g40)))
    return float((za + zb) * se * 100)


p_d1 = R["retention_1"]["rate_gate_30"]
d7 = R["retention_7"]
# Achieved power for the observed D7 difference (unpooled SE under H1).
se_d7 = np.sqrt(d7["rate_gate_30"] * (1 - d7["rate_gate_30"]) / len(g30)
                + d7["rate_gate_40"] * (1 - d7["rate_gate_40"]) / len(g40))
power_d7 = float(stats.norm.cdf(abs(d7["diff_pp"]) / 100 / se_d7 - za))
mde_d7 = mde_pp(d7["rate_gate_30"])
R["power"] = {
    "baseline_d1_retention_gate_30": p_d1,
    "mde_pp_at_80pct_power_baseline_d1": mde_pp(p_d1),
    "mde_pp_at_80pct_power_baseline_d7": mde_d7,
    "observed_d7_diff_pp": d7["diff_pp"],
    "achieved_power_for_observed_d7_diff": power_d7,
    "powered_for_observed_d7_diff": bool(abs(d7["diff_pp"]) >= mde_d7),
}
print(f"power: MDE={mde_pp(p_d1):.2f}pp @80% (D1 baseline); "
      f"MDE={mde_d7:.2f}pp @80% (D7 baseline); observed D7 diff "
      f"{d7['diff_pp']:+.2f}pp; achieved power={power_d7:.3f}; "
      f"powered={R['power']['powered_for_observed_d7_diff']}")

# --- guardrail: engagement ----------------------------------------------------
# Pre-declared rule (see memo.md): the move breaches the guardrail if
# gate_40 shows a statistically significant drop in mean rounds played or a
# significant rise in the share of users who never played a single round.
t = stats.ttest_ind(g40.sum_gamerounds, g30.sum_gamerounds, equal_var=False)
zero = prop_test(g30.sum_gamerounds.eq(0), g40.sum_gamerounds.eq(0))
R["guardrail_engagement"] = {
    "mean_rounds_gate_30": float(g30.sum_gamerounds.mean()),
    "mean_rounds_gate_40": float(g40.sum_gamerounds.mean()),
    "mean_diff": float(g40.sum_gamerounds.mean() - g30.sum_gamerounds.mean()),
    "welch_t_p": float(t.pvalue),
    "zero_round_share_gate_30": float(g30.sum_gamerounds.eq(0).mean()),
    "zero_round_share_gate_40": float(g40.sum_gamerounds.eq(0).mean()),
    "zero_round_share_test": zero,
    "breach": bool((t.pvalue < ALPHA and g40.sum_gamerounds.mean()
                    < g30.sum_gamerounds.mean())
                   or (zero["p_value"] < ALPHA and zero["diff_pp"] > 0)),
}
g = R["guardrail_engagement"]
print(f"guardrail: mean rounds 30={g['mean_rounds_gate_30']:.2f} "
      f"40={g['mean_rounds_gate_40']:.2f} (Welch p={g['welch_t_p']:.3g}); "
      f"zero-round share diff={zero['diff_pp']:+.2f}pp (p={zero['p_value']:.3g}); "
      f"breach={g['breach']}")

# --- bootstrap CI for the D7 difference --------------------------------------
rng = np.random.default_rng(SEED)
a = g30.retention_7.to_numpy()
b = g40.retention_7.to_numpy()
# Retention is binary, so a resample's mean is Binomial(n, p_hat)/n exactly;
# drawing counts directly is the same bootstrap, just fast.
boots = (rng.binomial(len(b), b.mean(), 10_000) / len(b)
         - rng.binomial(len(a), a.mean(), 10_000) / len(a)) * 100
blo, bhi = np.percentile(boots, [2.5, 97.5])
R["retention_7_bootstrap"] = {
    "n_resamples": 10_000, "seed": SEED,
    "diff_pp": float(boots.mean()),
    "ci95_pp": [float(blo), float(bhi)],
    "share_of_resamples_diff_below_0": float((boots < 0).mean()),
}
print(f"bootstrap D7 diff: mean={boots.mean():+.2f}pp "
      f"CI[{blo:+.2f},{bhi:+.2f}]; P(diff<0)={np.mean(boots < 0):.3f}")

# --- figures ------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(6, 4))
for i, k in enumerate(("retention_1", "retention_7")):
    r = R[k]
    rates = [r["rate_gate_30"] * 100, r["rate_gate_40"] * 100]
    ses = [np.sqrt(r["rate_gate_30"] * (1 - r["rate_gate_30"]) / len(g30)) * 100,
           np.sqrt(r["rate_gate_40"] * (1 - r["rate_gate_40"]) / len(g40)) * 100]
    x = np.arange(2) + i * 0.9
    ax.bar(x, rates, width=0.35, yerr=ses, capsize=4,
           label="Day 1" if i == 0 else "Day 7")
ax.set_xticks([0.45, 1.35]); ax.set_xticklabels(["gate_30", "gate_40"])
ax.set_ylabel("retention (%)"); ax.legend(); ax.set_title("Retention by arm (95% CI)")
fig.tight_layout(); fig.savefig(ROOT / "figures" / "retention_by_arm.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 4))
bins = np.logspace(0, np.log10(df.sum_gamerounds.max() + 1), 40)
for grp, lab in ((g30, "gate_30"), (g40, "gate_40")):
    ax.hist(grp.sum_gamerounds[grp.sum_gamerounds > 0], bins=bins,
            alpha=0.6, label=lab, density=True)
ax.set_xscale("log"); ax.set_xlabel("game rounds in first 14 days (log scale, >0 only)")
ax.set_ylabel("density"); ax.legend()
ax.set_title("Engagement distribution by arm (guardrail)")
fig.tight_layout(); fig.savefig(ROOT / "figures" / "gamerounds_distribution.png", dpi=150)
plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 4))
ax.hist(boots, bins=50, color="#4477aa")
ax.axvline(0, color="red", lw=1.5)
ax.set_xlabel("bootstrap D7 retention difference, gate_40 - gate_30 (pp)")
ax.set_title("Bootstrap distribution of the D7 difference")
fig.tight_layout(); fig.savefig(ROOT / "figures" / "bootstrap_d7.png", dpi=150)
plt.close(fig)

(ROOT / "outputs").mkdir(exist_ok=True)
(ROOT / "outputs" / "results.json").write_text(json.dumps(R, indent=2) + "\n")
print("wrote outputs/results.json and figures/*.png")
