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
# Pre-declared rule (see docs/experiment_plan.md): the move breaches the
# guardrail if
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

# --- SRM: chi-square test of the arm split -----------------------------------
# The split is 44,700 / 45,489 against a designed 50/50. A binomial test
# (above) and the standard chi-square goodness-of-fit SRM check are the
# same question; report the chi-square form because that is what
# experimentation platforms alarm on, judged at the usual p < 0.01
# (investigate) and p < 0.001 (hard alarm) thresholds.
n_exp = len(df) / 2
chi2 = float(((len(g30) - n_exp) ** 2 + (len(g40) - n_exp) ** 2) / n_exp)
srm_p = float(stats.chi2.sf(chi2, df=1))
R["srm"] = {
    "n_expected_per_arm": n_exp,
    "chi2": chi2,
    "p_value": srm_p,
    "split_pct_gate_30": float(len(g30) / len(df) * 100),
    "split_pct_gate_40": float(len(g40) / len(df) * 100),
    "flags_at_0_01": bool(srm_p < 0.01),
    "flags_at_0_001": bool(srm_p < 0.001),
}
print(f"srm: chi2={chi2:.2f} p={srm_p:.4f} "
      f"(flags at 0.01: {R['srm']['flags_at_0_01']}, "
      f"at 0.001: {R['srm']['flags_at_0_001']})")

# --- sensitivity to the split: IPW reweighting to 50/50 -----------------------
# Weight each arm to a 50/50 target: w = 0.5 / arm_share, Hajek estimator
# for the weighted arm rates, linearization variance. Note what this can
# and cannot do: the weights are constant within an arm, so the weighted
# arm rates equal the raw arm rates exactly and the point estimate cannot
# move; the check confirms the difference is not an artifact of how the
# two arms are pooled, and the trim check below probes the part that
# weighting cannot reach (dependence on the excess treatment users).


def hajek_rate(y: pd.Series, w: float):
    wsum = w * len(y)
    p = float((w * y).sum() / wsum)
    var = float((w ** 2 * (y - p) ** 2).sum() / wsum ** 2)
    n_eff = float(wsum ** 2 / (w ** 2 * len(y)))
    return p, var, n_eff


share30, share40 = len(g30) / len(df), len(g40) / len(df)
w30, w40 = 0.5 / share30, 0.5 / share40
ip30, iv30, ne30 = hajek_rate(g30.retention_7, w30)
ip40, iv40, ne40 = hajek_rate(g40.retention_7, w40)
idiff = (ip40 - ip30) * 100
ise = np.sqrt(iv30 + iv40) * 100
R["sensitivity_ipw_retention_7"] = {
    "method": "inverse-probability weights w = 0.5 / arm_share, "
              "Hajek weighted rates, linearization (sandwich) variance",
    "weight_gate_30": float(w30), "weight_gate_40": float(w40),
    "rate_gate_30_weighted": ip30, "rate_gate_40_weighted": ip40,
    "diff_pp": float(idiff),
    "ci95_pp": [float(idiff - za * ise), float(idiff + za * ise)],
    "effective_n_gate_30": ne30, "effective_n_gate_40": ne40,
    "conclusion_holds": bool(idiff < 0 and idiff + za * ise < 0),
}
print(f"sensitivity IPW D7: diff={idiff:+.2f}pp "
      f"CI[{idiff - za * ise:+.2f},{idiff + za * ise:+.2f}] "
      f"conclusion_holds={R['sensitivity_ipw_retention_7']['conclusion_holds']}")

# --- sensitivity to the split: trim gate_40 to a 44,700 / 44,700 design -------
# Repeatedly draw a random 44,700-player subset of gate_40 (seeded, exact
# hypergeometric draws of the retained count) and recompute the D7 test.
# If the verdict depended on the 789 excess treatment players, it would
# wobble here; a real dependence would show up as mass near or above zero.
rng_trim = np.random.default_rng(SEED + 1)
x40 = int(g40.retention_7.sum())
x30 = int(g30.retention_7.sum())
p30 = x30 / len(g30)
k_trim = rng_trim.hypergeometric(x40, len(g40) - x40, len(g30), size=1_000)
pt_trim = k_trim / len(g30)
diffs_trim = (pt_trim - p30) * 100
p_pool = (k_trim + x30) / (2 * len(g30))
se_pool = np.sqrt(p_pool * (1 - p_pool) * 2 / len(g30))
z_trim = (pt_trim - p30) / se_pool
p_trim = 2 * stats.norm.sf(np.abs(z_trim))
R["sensitivity_trim_retention_7"] = {
    "method": "1,000 seeded random trims of gate_40 to n = 44,700 "
              "(hypergeometric draws), two-proportion z-test per trim",
    "n_trims": 1_000, "seed": SEED + 1,
    "mean_diff_pp": float(diffs_trim.mean()),
    "diff_pp_percentiles_2_5_97_5": [float(np.percentile(diffs_trim, 2.5)),
                                     float(np.percentile(diffs_trim, 97.5))],
    "share_of_trims_diff_below_0": float((diffs_trim < 0).mean()),
    "share_of_trims_significant_at_0_05": float((p_trim < ALPHA).mean()),
    "conclusion_holds": bool(np.percentile(diffs_trim, 97.5) < 0
                             and (p_trim < ALPHA).mean() > 0.95),
}
print(f"sensitivity trim D7: mean diff={diffs_trim.mean():+.2f}pp, "
      f"95% of trims in [{np.percentile(diffs_trim, 2.5):+.2f},"
      f"{np.percentile(diffs_trim, 97.5):+.2f}], significant in "
      f"{(p_trim < ALPHA).mean():.1%} of trims, "
      f"conclusion_holds={R['sensitivity_trim_retention_7']['conclusion_holds']}")

# --- retention curve: D1 -> D7 decay by arm -----------------------------------
# Two observed points per arm (day 1, day 7) plus the conditional survival
# of day-1 returners to day 7, from the joint flags.
cond30 = float(g30.loc[g30.retention_1 == 1, "retention_7"].mean())
cond40 = float(g40.loc[g40.retention_1 == 1, "retention_7"].mean())
R["retention_curve"] = {
    "days": [1, 7],
    "gate_30_pct": [R["retention_1"]["rate_gate_30"] * 100,
                    R["retention_7"]["rate_gate_30"] * 100],
    "gate_40_pct": [R["retention_1"]["rate_gate_40"] * 100,
                    R["retention_7"]["rate_gate_40"] * 100],
    "d7_rate_among_d1_retained_gate_30": cond30,
    "d7_rate_among_d1_retained_gate_40": cond40,
}
print(f"retention curve: D1->D7 gate_30 "
      f"{R['retention_curve']['gate_30_pct'][0]:.2f}% -> "
      f"{R['retention_curve']['gate_30_pct'][1]:.2f}% "
      f"(conditional {cond30:.3f}); gate_40 "
      f"{R['retention_curve']['gate_40_pct'][0]:.2f}% -> "
      f"{R['retention_curve']['gate_40_pct'][1]:.2f}% "
      f"(conditional {cond40:.3f})")

# --- follow-up experiment sizing ----------------------------------------------
# Per-arm n to detect a 0.5pp D7 difference at 80% power, alpha = 0.05
# two-sided, normal approximation, from the observed D7 control rate.
import math
p_base = d7["rate_gate_30"]
delta = 0.005
p_alt = p_base + delta
n_arm = math.ceil((za + zb) ** 2
                  * (p_base * (1 - p_base) + p_alt * (1 - p_alt))
                  / delta ** 2)
R["followup_sample_size"] = {
    "metric": "day-7 retention",
    "baseline_rate_gate_30": p_base,
    "mde_pp": delta * 100,
    "alpha": ALPHA, "power": 0.80,
    "n_per_arm": int(n_arm),
    "n_total": int(2 * n_arm),
}
print(f"follow-up sizing: {n_arm:,}/arm ({2 * n_arm:,} total) to detect "
      f"0.5pp on D7 at 80% power from baseline {p_base:.3f}")

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

rc = R["retention_curve"]
fig, ax = plt.subplots(figsize=(6, 4))
for rates, lab, mk in ((rc["gate_30_pct"], "gate_30", "o"),
                       (rc["gate_40_pct"], "gate_40", "s")):
    ax.plot(rc["days"], rates, marker=mk, lw=2, label=lab)
    for d, r in zip(rc["days"], rates):
        ax.annotate(f"{r:.2f}%", (d, r), textcoords="offset points",
                    xytext=(0, 8), ha="center")
ax.set_xticks([1, 7]); ax.set_xlabel("day after install")
ax.set_ylabel("retention (%)")
ax.set_title("Retention decay by arm: day 1 to day 7")
ax.legend(); ax.set_ylim(0, 55)
fig.tight_layout(); fig.savefig(ROOT / "figures" / "retention_curve.png", dpi=150)
plt.close(fig)

(ROOT / "outputs").mkdir(exist_ok=True)
(ROOT / "outputs" / "results.json").write_text(json.dumps(R, indent=2) + "\n")
print("wrote outputs/results.json and figures/*.png")
