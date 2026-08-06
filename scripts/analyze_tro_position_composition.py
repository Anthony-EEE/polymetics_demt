#!/usr/bin/env python3
"""Pre-registered Stage 2c Position composition analysis."""

import itertools
import json
import math
import re
import statistics
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tro_position_composition import (  # noqa: E402
    ANALYSIS, CONDITION_ORDER, CONDITIONS, MANIFESTS, NEW_CONDITIONS,
    ROLLOUT_SEEDS, SEEDS, read_json, sha256, summary_path, write_frozen_json,
)


STARTS = ("START15", "START25", "START35")
APPROACHES = ("APP3P6", "APP6", "APP8P4")
SCOPES = ("combined", "inner", "outer")
CONTRASTS = {
    "I_tight_15": ("START15", "APP3P6"),
    "I_tight_35": ("START35", "APP3P6"),
    "I_wide_15": ("START15", "APP8P4"),
    "I_wide_35": ("START35", "APP8P4"),
}


def condition(start, approach):
    return f"{start}_{approach}"


def wilson(successes, n, z=1.959963984540054):
    p = successes / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def validation_history(checkpoint):
    run_dir = Path(
        checkpoint.get("run_dir", Path(checkpoint["checkpoint_path"]).parents[1])
    )
    log_path = run_dir / "logs" / "log.txt"
    history = []
    if log_path.is_file():
        epoch = None
        for line in log_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            match = re.search(r"Validation Epoch\s+(\d+)", line)
            if match:
                epoch = int(match.group(1))
                continue
            match = re.search(r'"Loss":\s*([-+0-9.eE]+)', line)
            if match and epoch is not None:
                history.append({"epoch": epoch, "loss": float(match.group(1))})
                epoch = None
    return {
        "available": bool(history),
        "log_path": str(log_path.resolve()),
        "log_sha256": sha256(log_path) if log_path.is_file() else None,
        "epochs": history,
    }


def load_surface(surface):
    banks = ("inner", "outer") if surface == "common_absolute" else ("id", "ood")
    rows = {}
    sources = []
    for seed in SEEDS:
        for cond in CONDITION_ORDER:
            keyed = {}
            for rollout_seed in ROLLOUT_SEEDS:
                for bank in banks:
                    path = summary_path(
                        surface, seed, rollout_seed, bank, cond
                    )
                    payload = read_json(path)
                    sources.append({
                        "canonical_seed": seed, "condition": cond,
                        "rollout_seed": rollout_seed, "bank": bank,
                        "path": str(path.resolve()), "sha256": sha256(path),
                    })
                    for row in payload["rollouts"]:
                        key = (
                            f"rollout_seed{rollout_seed}/{bank}/"
                            f"{row['state_id']}"
                        )
                        if key in keyed:
                            raise ValueError(f"Duplicate trial: {seed}/{cond}/{key}")
                        keyed[key] = row
            if len(keyed) != 250:
                raise ValueError(f"{surface}: {seed}/{cond} != 250 rows")
            rows[(seed, cond)] = keyed
    expected = set(next(iter(rows.values())))
    if any(set(value) != expected for value in rows.values()):
        if surface == "common_absolute":
            raise ValueError("Common-absolute full grid is not exactly paired")
        # RMAX40 cross-Start state IDs differ by design. Pairing is same-Start.
        for start in STARTS:
            keys = [
                set(rows[(seed, condition(start, app))])
                for seed in SEEDS for app in APPROACHES
            ]
            if any(value != keys[0] for value in keys[1:]):
                raise ValueError(f"RMAX40 {start} family is not paired")
    return rows, sources, banks


def rate(rows, bank=None):
    selected = [
        row for key, row in rows.items()
        if bank is None or f"/{bank}/" in key
    ]
    successes = sum(bool(row["success"]) for row in selected)
    return {
        "successes": successes, "trials": len(selected),
        "rate": successes / len(selected),
        "wilson_95_rollout_description": wilson(successes, len(selected)),
    }


def bootstrap(values, name):
    rng = np.random.default_rng(20260726 + sum(map(ord, name)))
    array = np.asarray(values)
    samples = rng.choice(array, size=(100000, 5), replace=True).mean(axis=1)
    return {
        "cluster": "canonical dataset-policy seed",
        "draws": 100000,
        "rng_seed": 20260726 + sum(map(ord, name)),
        "percentile_95": [
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        ],
    }


def trial_interaction(common, seed, start, approach, bank=None):
    keys = sorted(common[(seed, condition(start, approach))])
    if bank:
        keys = [key for key in keys if f"/{bank}/" in key]
    values = []
    for key in keys:
        value = (
            int(common[(seed, condition(start, approach))][key]["success"])
            - int(common[(seed, condition(start, "APP6"))][key]["success"])
            - int(common[(seed, condition("START25", approach))][key]["success"])
            + int(common[(seed, condition("START25", "APP6"))][key]["success"])
        )
        values.append(value)
    counts = {str(value): values.count(value) for value in (-2, -1, 0, 1, 2)}
    return {
        "trials": len(values), "value_counts": counts,
        "sum": sum(values), "mean": statistics.mean(values),
    }


def contrast_value(policy_stats, seed, start, approach, scope):
    def value(start_value, approach_value):
        return policy_stats[(seed, condition(start_value, approach_value))][scope][
            "rate"
        ]
    return (
        value(start, approach) - value(start, "APP6")
        - value("START25", approach) + value("START25", "APP6")
    )


def same_nonzero_sign_as_mean(values, mean):
    return int(sum(
        value != 0 and np.sign(value) == np.sign(mean) for value in values
    ))


def paired_table(left, right, bank=None):
    keys = sorted(left)
    if bank:
        keys = [key for key in keys if f"/{bank}/" in key]
    pairs = [
        (bool(left[key]["success"]), bool(right[key]["success"])) for key in keys
    ]
    return {
        "both_success": sum(a and b for a, b in pairs),
        "left_only": sum(a and not b for a, b in pairs),
        "right_only": sum(not a and b for a, b in pairs),
        "both_failure": sum(not a and not b for a, b in pairs),
    }


def pareto_front(condition_stats):
    front = []
    for cond, values in condition_stats.items():
        dominated = any(
            other != cond
            and other_values["id"]["mean_rate"] >= values["id"]["mean_rate"]
            and other_values["ood"]["mean_rate"] >= values["ood"]["mean_rate"]
            and (
                other_values["id"]["mean_rate"] > values["id"]["mean_rate"]
                or other_values["ood"]["mean_rate"] > values["ood"]["mean_rate"]
            )
            for other, other_values in condition_stats.items()
        )
        if not dominated:
            front.append(cond)
    return front


def figures(condition_stats, contrasts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = ANALYSIS / "figures"
    output.mkdir(parents=True, exist_ok=True)
    matrix = np.asarray([
        [condition_stats[condition(start, app)]["combined"]["mean_rate"]
         for app in APPROACHES] for start in STARTS
    ])
    fig, ax = plt.subplots(figsize=(7, 4.8))
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap="viridis")
    ax.set_xticks(range(3), APPROACHES)
    ax.set_yticks(range(3), STARTS)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{matrix[i, j]:.3f}", ha="center", va="center",
                    color="white" if matrix[i, j] < .55 else "black")
    ax.set_title("Common-absolute mean policy success")
    fig.colorbar(image, ax=ax, label="success rate")
    fig.tight_layout()
    path1 = output / "common_absolute_response_surface.png"
    fig.savefig(path1, dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.8))
    x = np.arange(5)
    for name, values in contrasts.items():
        ax.plot(x, values["canonical_seed_values"], marker="o", label=name)
    ax.axhline(0, color="black", linewidth=.8)
    ax.axhline(.05, color="grey", linestyle="--", linewidth=.8)
    ax.axhline(-.05, color="grey", linestyle="--", linewidth=.8)
    ax.set_xticks(x, [f"seed{seed}" for seed in SEEDS])
    ax.set_ylabel("difference-in-differences")
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    path2 = output / "interaction_contrasts_by_seed.png"
    fig.savefig(path2, dpi=180)
    plt.close(fig)
    return {
        path.name: sha256(path) for path in (path1, path2)
    }


def analyze():
    merge = read_json(MANIFESTS / "merge_validation.json")
    if merge["status"] != "valid":
        raise RuntimeError("Strict merge must pass before analysis")
    common, common_sources, common_banks = load_surface("common_absolute")
    rmax, rmax_sources, rmax_banks = load_surface("rmax40")
    checkpoints = read_json(MANIFESTS / "checkpoints.json")
    cp = {
        (int(row["canonical_seed"]), row["condition"]): row
        for row in checkpoints["checkpoints"]
    }
    policy_stats = {}
    for seed in SEEDS:
        for cond in CONDITION_ORDER:
            policy_stats[(seed, cond)] = {
                "combined": rate(common[(seed, cond)]),
                "inner": rate(common[(seed, cond)], "inner"),
                "outer": rate(common[(seed, cond)], "outer"),
                "id": rate(rmax[(seed, cond)], "id"),
                "ood": rate(rmax[(seed, cond)], "ood"),
                "checkpoint": {
                    "epoch": cp[(seed, cond)]["epoch"],
                    "path": cp[(seed, cond)]["checkpoint_path"],
                    "sha256": cp[(seed, cond)]["checkpoint_sha256"],
                    "reused_policy": cp[(seed, cond)]["reused_policy"],
                },
                "validation_history": validation_history(cp[(seed, cond)]),
            }
    condition_stats = {}
    for cond in CONDITION_ORDER:
        condition_stats[cond] = {}
        for scope in ("combined", "inner", "outer", "id", "ood"):
            values = [policy_stats[(seed, cond)][scope]["rate"] for seed in SEEDS]
            condition_stats[cond][scope] = {
                "canonical_seed_rates": values,
                "mean_rate": statistics.mean(values),
                "sample_std_rate_ddof1": statistics.stdev(values),
            }
        condition_stats[cond]["id_minus_ood_gap"] = (
            condition_stats[cond]["id"]["mean_rate"]
            - condition_stats[cond]["ood"]["mean_rate"]
        )
    contrasts = {}
    for name, (start, approach) in CONTRASTS.items():
        values = [
            contrast_value(policy_stats, seed, start, approach, "combined")
            for seed in SEEDS
        ]
        mean = statistics.mean(values)
        same_sign = same_nonzero_sign_as_mean(values, mean)
        contrasts[name] = {
            "definition": (
                f"[r({start},{approach})-r({start},APP6)] - "
                f"[r(START25,{approach})-r(START25,APP6)]"
            ),
            "canonical_seed_values": values,
            "mean": mean, "sample_std_ddof1": statistics.stdev(values),
            "cluster_bootstrap": bootstrap(values, name),
            "same_nonzero_sign_as_mean": same_sign,
            "meets_abs_mean_margin": abs(mean) >= .05,
            "meets_sign_rule": same_sign >= 4,
            "reproducible_interaction_signal":
                abs(mean) >= .05 and same_sign >= 4,
            "decomposition": {
                scope: {
                    "canonical_seed_values": [
                        contrast_value(policy_stats, seed, start, approach, scope)
                        for seed in SEEDS
                    ],
                    "mean": statistics.mean(
                        contrast_value(
                            policy_stats, seed, start, approach, scope
                        ) for seed in SEEDS
                    ),
                } for scope in ("inner", "outer")
            },
            "exact_paired_interaction_discordances": {
                str(seed): {
                    scope: trial_interaction(
                        common, seed, start, approach,
                        None if scope == "combined" else scope
                    ) for scope in SCOPES
                } for seed in SEEDS
            },
            "component_pair_discordances": {
                str(seed): {
                    "target_start_row": paired_table(
                        common[(seed, condition(start, approach))],
                        common[(seed, condition(start, "APP6"))],
                    ),
                    "START25_baseline_row": paired_table(
                        common[(seed, condition("START25", approach))],
                        common[(seed, condition("START25", "APP6"))],
                    ),
                } for seed in SEEDS
            },
        }
    classification = (
        "interaction"
        if any(row["reproducible_interaction_signal"] for row in contrasts.values())
        else "no reproducible interaction"
    )
    descriptive_model = {
        "baseline_intercept_START25_APP6":
            condition_stats["START25_APP6"]["combined"]["mean_rate"],
        "start_main_effects_at_APP6": {
            start: (
                condition_stats[condition(start, "APP6")]["combined"]["mean_rate"]
                - condition_stats["START25_APP6"]["combined"]["mean_rate"]
            ) for start in ("START15", "START35")
        },
        "approach_main_effects_at_START25": {
            approach: (
                condition_stats[condition("START25", approach)]["combined"][
                    "mean_rate"
                ] - condition_stats["START25_APP6"]["combined"]["mean_rate"]
            ) for approach in ("APP3P6", "APP8P4")
        },
        "interaction_terms": {
            name: row["mean"] for name, row in contrasts.items()
        },
    }
    sensitivity = {}
    for label, seeds in (
        ("seed1_3", (1, 2, 3)), ("alias4_5", (4, 5))
    ):
        sensitivity[label] = {
            name: {
                "canonical_seeds": list(seeds),
                "values": [
                    contrast_value(
                        policy_stats, seed, start, approach, "combined"
                    ) for seed in seeds
                ],
                "mean": statistics.mean(
                    contrast_value(
                        policy_stats, seed, start, approach, "combined"
                    ) for seed in seeds
                ),
            } for name, (start, approach) in CONTRASTS.items()
        }
    figure_hashes = figures(condition_stats, contrasts)
    report = {
        "schema_version": 1, "status": "complete",
        "protocol_id": (
            "tro_stage2_position_composition_missing_cells_v3_"
            "continue_candidate_stream_until_30_successes"
        ),
        "interaction_classification": classification,
        "classification_rule": {
            "delta_interaction": .05,
            "same_nonzero_sign_as_mean_required": 4,
        },
        "coverage": {
            "new_tasks": 400, "new_rows": 10000,
            "full_common_absolute_policies": 45,
            "full_common_absolute_rows": 11250,
            "full_rmax40_policies": 45, "full_rmax40_rows": 11250,
        },
        "independent_unit": "canonical dataset-policy seed",
        "nested_trials": "rollout seeds and rows are deployment trials",
        "common_absolute_policy_matrix": {
            f"seed{seed}/{cond}": policy_stats[(seed, cond)]
            for cond in CONDITION_ORDER for seed in SEEDS
        },
        "common_absolute_condition_summary": condition_stats,
        "within_row_approach_rankings": {
            start: sorted(
                APPROACHES,
                key=lambda app: -condition_stats[condition(start, app)][
                    "combined"
                ]["mean_rate"],
            ) for start in STARTS
        },
        "within_column_start_rankings": {
            approach: sorted(
                STARTS,
                key=lambda start: -condition_stats[condition(start, approach)][
                    "combined"
                ]["mean_rate"],
            ) for approach in APPROACHES
        },
        "primary_interaction_contrasts": contrasts,
        "categorical_descriptive_model": descriptive_model,
        "condition_relative_rmax40": {
            "condition_summary": {
                cond: {
                    "id": condition_stats[cond]["id"],
                    "ood": condition_stats[cond]["ood"],
                    "id_minus_ood_gap":
                        condition_stats[cond]["id_minus_ood_gap"],
                } for cond in CONDITION_ORDER
            },
            "pareto_front_maximize_id_and_ood": pareto_front(condition_stats),
            "cross_start_balanced_scores_not_common_absolute": True,
        },
        "policy_level_variance": {
            cond: {
                scope: condition_stats[cond][scope]["sample_std_rate_ddof1"]
                for scope in ("combined", "inner", "outer", "id", "ood")
            } for cond in CONDITION_ORDER
        },
        "seed1_3_vs_alias4_5_sensitivity": sensitivity,
        "feasibility_pairing_rng_audit": {
            "feasibility_audit_sha256":
                sha256(MANIFESTS / "feasibility_audit.json"),
            "common_absolute_exact_pairing": True,
            "rmax40_same_start_absolute_pairing": True,
            "runtime_and_point_cloud_rng_pairing": True,
        },
        "figures": figure_hashes,
        "source_summary_counts": {
            "common_absolute": len(common_sources),
            "rmax40": len(rmax_sources),
        },
    }
    write_frozen_json(ANALYSIS / "comparison.json", report)
    lines = [
        "# T-RO Stage 2c Position Composition Summary", "",
        f"**Interaction classification:** `{classification}`", "",
        "The primary common-absolute analysis uses five canonical dataset-policy "
        "seeds; rollout seeds and individual rows remain nested deployment trials.",
        "", "## Frozen interaction contrasts", "",
        "| Contrast | Seed values | Mean | SD | Bootstrap 95% | Sign | Signal |",
        "|---|---|---:|---:|---|---:|---|",
    ]
    for name, row in contrasts.items():
        interval = row["cluster_bootstrap"]["percentile_95"]
        lines.append(
            f"| `{name}` | {', '.join(f'{v:.3f}' for v in row['canonical_seed_values'])} "
            f"| {row['mean']:.3f} | {row['sample_std_ddof1']:.3f} "
            f"| [{interval[0]:.3f}, {interval[1]:.3f}] "
            f"| {row['same_nonzero_sign_as_mean']}/5 "
            f"| {'yes' if row['reproducible_interaction_signal'] else 'no'} |"
        )
    lines += [
        "", "## Common-absolute condition means", "",
        "| Condition | Combined | Inner | Outer |",
        "|---|---:|---:|---:|",
    ]
    for cond in CONDITION_ORDER:
        lines.append(
            f"| `{cond}` | {condition_stats[cond]['combined']['mean_rate']:.3f} "
            f"| {condition_stats[cond]['inner']['mean_rate']:.3f} "
            f"| {condition_stats[cond]['outer']['mean_rate']:.3f} |"
        )
    lines += [
        "", "## Condition-relative RMAX40", "",
        "| Condition | ID | OOD | ID-OOD |",
        "|---|---:|---:|---:|",
    ]
    for cond in CONDITION_ORDER:
        lines.append(
            f"| `{cond}` | {condition_stats[cond]['id']['mean_rate']:.3f} "
            f"| {condition_stats[cond]['ood']['mean_rate']:.3f} "
            f"| {condition_stats[cond]['id_minus_ood_gap']:.3f} |"
        )
    lines += [
        "",
        "RMAX40 is secondary and condition-relative; cross-Start balanced scores "
        "are not a common absolute deployment distribution.",
        "",
        "Wilson intervals in `comparison.json` are rollout-level descriptions only.",
    ]
    summary = "\n".join(lines) + "\n"
    path = ANALYSIS / "summary.md"
    if path.exists() and path.read_text(encoding="utf-8") != summary:
        raise FileExistsError(f"Refusing to replace frozen analysis: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(summary, encoding="utf-8")
    print(json.dumps({
        "classification": classification,
        "contrasts": {name: row["mean"] for name, row in contrasts.items()},
        "pareto_front": report["condition_relative_rmax40"][
            "pareto_front_maximize_id_and_ood"
        ],
    }, indent=2))


if __name__ == "__main__":
    analyze()
