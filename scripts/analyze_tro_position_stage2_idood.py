#!/usr/bin/env python3
"""Strict merge and policy-level analysis for Stage 2 condition-relative ID/OOD."""

import argparse
import hashlib
import itertools
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from tro_position_stage2_idood import (  # noqa: E402
    BANKS,
    CONDITIONS,
    EXPERIMENT,
    MANIFESTS,
    NUM_STATES,
    OLD_ANALYSIS,
    ROLLOUT_SEEDS,
    SOURCE_CHECKPOINTS,
    SOURCE_MANIFESTS,
    START_RADII,
    bank_bounds,
    evaluator_args,
    manifest_id,
    manifest_path,
    radius_from_quantile,
    sha256,
    validate_manifests,
)
from eval_abla1_trained_policies import evaluation_protocol  # noqa: E402


ANALYSIS = EXPERIMENT / "analysis"
ROLLOUT_ROOT = (
    ROOT
    / "dataset"
    / "tro_position_stage2_axial_idood_rerollout"
    / "rmax40"
    / "rollouts"
    / "formal"
)
CANONICAL_SEEDS = (1, 2, 3, 4, 5)
CONDITION_ORDER = tuple(CONDITIONS)
CONDITION_START_RADIUS = CONDITIONS


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def wilson(successes, total, z=1.959963984540054):
    if total <= 0:
        return [None, None]
    rate = successes / total
    denominator = 1.0 + z * z / total
    center = (rate + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(
        rate * (1.0 - rate) / total
        + z * z / (4.0 * total * total)
    ) / denominator
    return [center - margin, center + margin]


def row_stats(rows):
    successes = sum(bool(row["success"]) for row in rows)
    total = len(rows)
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total,
        "wilson_95_rollout_level_description": wilson(successes, total),
    }


def policy_id(seed, condition):
    return f"seed{seed}/{condition}"


def checkpoint_index():
    unified = read_json(SOURCE_CHECKPOINTS)
    if len(unified["checkpoints"]) != 25:
        raise ValueError("Expected 25 source checkpoints")
    result = {}
    for row in unified["checkpoints"]:
        key = (int(row["canonical_seed"]), row["condition"])
        actual = sha256(row["checkpoint_path"])
        if actual != row["checkpoint_sha256"]:
            raise ValueError(f"{key}: checkpoint hash mismatch")
        result[key] = row
    if len(result) != 25:
        raise ValueError("Checkpoint key matrix is not 5 x 5")
    return result


def summary_path(canonical_seed, rollout_seed, bank, condition):
    return (
        ROLLOUT_ROOT
        / f"seed{canonical_seed}"
        / f"rollout_seed{rollout_seed}"
        / bank
        / f"spatial_{condition}_seed{rollout_seed}_n25.json"
    )


def normalized_signature(record):
    return (
        int(record["normalized_state_index"]),
        record["normalized_state_id"],
        int(record["candidate_index"]),
        float(record["area_quantile"]),
        float(record["theta_rad"]),
        int(record["rng_seed"]),
        int(record["point_cloud_rng_seed"]),
    )


def validate_and_collect():
    manifest_report = validate_manifests()
    checkpoints = checkpoint_index()
    policy_rows = {
        policy_id(seed, condition): {"id": {}, "ood": {}}
        for seed in CANONICAL_SEEDS
        for condition in CONDITION_ORDER
    }
    source_summaries = []
    validated_tasks = 0
    same_start_assertions = []
    cross_start_assertions = []

    for canonical_seed in CANONICAL_SEEDS:
        checkpoint_view = SOURCE_MANIFESTS / f"checkpoints_seed{canonical_seed}.json"
        view_payload = read_json(checkpoint_view)
        if view_payload["unified_checkpoint_manifest_sha256"] != sha256(
            SOURCE_CHECKPOINTS
        ):
            raise ValueError(f"seed{canonical_seed}: unified checkpoint view hash")
        for rollout_seed in ROLLOUT_SEEDS:
            for bank in BANKS:
                manifests = {
                    radius: read_json(manifest_path(radius, rollout_seed, bank))
                    for radius in START_RADII
                }
                normalized = {
                    radius: [
                        normalized_signature(row)
                        for row in payload["shared_start_records"]
                    ]
                    for radius, payload in manifests.items()
                }
                if any(
                    normalized[radius] != normalized[START_RADII[0]]
                    for radius in START_RADII[1:]
                ):
                    raise ValueError("Cross-Start normalized manifest pairing")
                cross_start_assertions.append(
                    {
                        "canonical_seed": canonical_seed,
                        "rollout_seed": rollout_seed,
                        "bank": bank,
                        "paired_normalized_states": NUM_STATES,
                    }
                )

                summary_by_condition = {}
                for condition in CONDITION_ORDER:
                    radius = CONDITION_START_RADIUS[condition]
                    start_path = manifest_path(radius, rollout_seed, bank)
                    start = manifests[radius]
                    records = start["shared_start_records"]
                    path = summary_path(
                        canonical_seed, rollout_seed, bank, condition
                    )
                    summary = read_json(path)
                    source_summaries.append(str(path.resolve()))
                    expected_checkpoint = checkpoints[(canonical_seed, condition)]
                    expected_bank_id = manifest_id(radius, rollout_seed, bank)
                    if summary["condition"] != condition:
                        raise ValueError(f"{path}: condition mismatch")
                    if int(summary["block"]) != canonical_seed:
                        raise ValueError(f"{path}: canonical seed mismatch")
                    if summary["bank_id"] != expected_bank_id:
                        raise ValueError(f"{path}: bank ID mismatch")
                    if summary["start_manifest_sha256"] != sha256(start_path):
                        raise ValueError(f"{path}: start manifest hash mismatch")
                    summary_checkpoint_view = Path(
                        summary["checkpoint_manifest"]
                    ).resolve()
                    if summary_checkpoint_view != checkpoint_view.resolve():
                        raise ValueError(f"{path}: checkpoint view path mismatch")
                    if summary["checkpoint"] != expected_checkpoint[
                        "checkpoint_path"
                    ]:
                        raise ValueError(f"{path}: checkpoint path mismatch")
                    if summary["checkpoint_sha256"] != expected_checkpoint[
                        "checkpoint_sha256"
                    ]:
                        raise ValueError(f"{path}: checkpoint hash mismatch")
                    if summary["protocol"] != evaluation_protocol(
                        evaluator_args(
                            radius,
                            rollout_seed,
                            bank,
                            bank_id=expected_bank_id,
                        )
                    ):
                        raise ValueError(f"{path}: evaluator protocol mismatch")
                    rows = summary["rollouts"]
                    if len(rows) != NUM_STATES:
                        raise ValueError(f"{path}: expected 25 rollout rows")
                    if [row["state_id"] for row in rows] != [
                        row["state_id"] for row in records
                    ]:
                        raise ValueError(f"{path}: state order mismatch")
                    rollout_dir = path.parent / "rollouts" / condition
                    expected_files = {
                        f"rollout_{index:03d}.json"
                        for index in range(NUM_STATES)
                    }
                    actual_files = {
                        item.name for item in rollout_dir.glob("*.json")
                    }
                    if actual_files != expected_files:
                        raise ValueError(f"{path}: per-rollout file set mismatch")
                    for index, row in enumerate(rows):
                        record = records[index]
                        if row["paired_spec"] != record:
                            raise ValueError(f"{path}: paired spec mismatch")
                        if row["checkpoint_sha256"] != expected_checkpoint[
                            "checkpoint_sha256"
                        ]:
                            raise ValueError(f"{path}: row checkpoint mismatch")
                        if (
                            int(row["rng_seed"]) != int(record["rng_seed"])
                            or int(row["point_cloud_rng_seed"])
                            != int(record["point_cloud_rng_seed"])
                        ):
                            raise ValueError(f"{path}: RNG mismatch")
                        per_rollout = read_json(
                            rollout_dir / f"rollout_{index:03d}.json"
                        )
                        if per_rollout != row:
                            raise ValueError(f"{path}: per-rollout content mismatch")
                        key = (
                            f"rollout_seed{rollout_seed}/"
                            f"{record['normalized_state_id']}"
                        )
                        target = policy_rows[policy_id(canonical_seed, condition)][
                            bank
                        ]
                        if key in target:
                            raise ValueError(f"{path}: duplicate trial")
                        target[key] = row
                    summary_by_condition[condition] = summary
                    validated_tasks += 1

                start25_specs = [
                    [
                        row["paired_spec"]
                        for row in summary_by_condition[condition]["rollouts"]
                    ]
                    for condition in (
                        "START25_APP3P6",
                        "START25_APP6",
                        "START25_APP8P4",
                    )
                ]
                if any(specs != start25_specs[0] for specs in start25_specs[1:]):
                    raise ValueError("START25 absolute state/RNG pairing mismatch")
                same_start_assertions.append(
                    {
                        "canonical_seed": canonical_seed,
                        "rollout_seed": rollout_seed,
                        "bank": bank,
                        "conditions": [
                            "START25_APP3P6",
                            "START25_APP6",
                            "START25_APP8P4",
                        ],
                        "paired_absolute_states": NUM_STATES,
                    }
                )

    if validated_tasks != 250:
        raise ValueError(f"Expected 250 tasks, validated {validated_tasks}")
    for pid, banks in policy_rows.items():
        for bank in BANKS:
            if len(banks[bank]) != 125:
                raise ValueError(f"{pid}/{bank}: expected 125 trials")
    total_rows = sum(
        len(rows)
        for banks in policy_rows.values()
        for rows in banks.values()
    )
    if total_rows != 6250:
        raise ValueError(f"Expected 6,250 rows, got {total_rows}")
    return {
        "policy_rows": policy_rows,
        "checkpoints": checkpoints,
        "source_summaries": source_summaries,
        "validated_tasks": validated_tasks,
        "total_rows": total_rows,
        "manifest_report": manifest_report,
        "same_start_assertions": same_start_assertions,
        "cross_start_assertions": cross_start_assertions,
    }


def cluster_bootstrap(values, seed, draws=100000):
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(
        values, size=(draws, len(values)), replace=True
    ).mean(axis=1)
    return {
        "top_level_cluster": "canonical dataset-policy seed",
        "draws": draws,
        "rng_seed": seed,
        "observed_mean": float(values.mean()),
        "percentile_95": [
            float(np.quantile(samples, 0.025)),
            float(np.quantile(samples, 0.975)),
        ],
        "probability_mean_gt_zero": float(np.mean(samples > 0.0)),
    }


def paired_discordance(left_rows, right_rows):
    keys = sorted(left_rows)
    if set(keys) != set(right_rows):
        raise ValueError("Paired discordance keys differ")
    pairs = [
        (bool(left_rows[key]["success"]), bool(right_rows[key]["success"]))
        for key in keys
    ]
    return {
        "both_success": sum(a and b for a, b in pairs),
        "left_only": sum(a and not b for a, b in pairs),
        "right_only": sum((not a) and b for a, b in pairs),
        "both_failure": sum((not a) and (not b) for a, b in pairs),
    }


def pareto_front(conditions):
    front = []
    for candidate, row in conditions.items():
        dominated = any(
            other != candidate
            and other_row["id"]["mean_rate"] >= row["id"]["mean_rate"]
            and other_row["ood"]["mean_rate"] >= row["ood"]["mean_rate"]
            and (
                other_row["id"]["mean_rate"] > row["id"]["mean_rate"]
                or other_row["ood"]["mean_rate"] > row["ood"]["mean_rate"]
            )
            for other, other_row in conditions.items()
        )
        if not dominated:
            front.append(candidate)
    return front


def summarize(validated):
    policy_rows = validated["policy_rows"]
    checkpoints = validated["checkpoints"]
    policies = {}
    for canonical_seed in CANONICAL_SEEDS:
        for condition in CONDITION_ORDER:
            pid = policy_id(canonical_seed, condition)
            banks = policy_rows[pid]
            per_seed = {}
            for rollout_seed in ROLLOUT_SEEDS:
                per_seed[str(rollout_seed)] = {}
                for bank in BANKS:
                    rows = [
                        row
                        for key, row in banks[bank].items()
                        if key.startswith(f"rollout_seed{rollout_seed}/")
                    ]
                    per_seed[str(rollout_seed)][bank] = row_stats(rows)
            checkpoint = checkpoints[(canonical_seed, condition)]
            bank_stats = {bank: row_stats(list(banks[bank].values())) for bank in BANKS}
            id_rate = bank_stats["id"]["rate"]
            ood_rate = bank_stats["ood"]["rate"]
            policies[pid] = {
                "canonical_seed": canonical_seed,
                "source_collection_seed": int(
                    checkpoint["source_collection_seed"]
                ),
                "source_training_seed": int(
                    checkpoint["source_training_seed"]
                ),
                "condition": condition,
                "start_support_radius_m": CONDITION_START_RADIUS[condition],
                "checkpoint": {
                    "path": checkpoint["checkpoint_path"],
                    "sha256": checkpoint["checkpoint_sha256"],
                    "epoch": int(checkpoint["epoch"]),
                },
                "id": bank_stats["id"],
                "ood": bank_stats["ood"],
                "generalisation_gap_ood_minus_id": ood_rate - id_rate,
                "balanced_descriptive_score": 0.5 * (id_rate + ood_rate),
                "per_rollout_seed": per_seed,
                "rollout_seed_mean_and_sample_std": {
                    bank: {
                        "seed_rates": [
                            per_seed[str(seed)][bank]["rate"]
                            for seed in ROLLOUT_SEEDS
                        ],
                        "mean_rate": statistics.mean(
                            per_seed[str(seed)][bank]["rate"]
                            for seed in ROLLOUT_SEEDS
                        ),
                        "sample_std_rate_ddof1": statistics.stdev(
                            per_seed[str(seed)][bank]["rate"]
                            for seed in ROLLOUT_SEEDS
                        ),
                    }
                    for bank in BANKS
                },
            }

    condition_stats = {}
    for condition in CONDITION_ORDER:
        id_rates = [
            policies[policy_id(seed, condition)]["id"]["rate"]
            for seed in CANONICAL_SEEDS
        ]
        ood_rates = [
            policies[policy_id(seed, condition)]["ood"]["rate"]
            for seed in CANONICAL_SEEDS
        ]
        gaps = [
            policies[policy_id(seed, condition)][
                "generalisation_gap_ood_minus_id"
            ]
            for seed in CANONICAL_SEEDS
        ]
        balanced = [
            policies[policy_id(seed, condition)][
                "balanced_descriptive_score"
            ]
            for seed in CANONICAL_SEEDS
        ]
        condition_stats[condition] = {
            "start_support_radius_m": CONDITION_START_RADIUS[condition],
            "id": {
                "policy_rates": id_rates,
                "mean_rate": statistics.mean(id_rates),
                "sample_std_rate_ddof1": statistics.stdev(id_rates),
            },
            "ood": {
                "policy_rates": ood_rates,
                "mean_rate": statistics.mean(ood_rates),
                "sample_std_rate_ddof1": statistics.stdev(ood_rates),
            },
            "generalisation_gap_ood_minus_id": {
                "policy_values": gaps,
                "mean": statistics.mean(gaps),
                "sample_std_ddof1": statistics.stdev(gaps),
            },
            "balanced_descriptive_score": {
                "policy_values": balanced,
                "mean": statistics.mean(balanced),
                "sample_std_ddof1": statistics.stdev(balanced),
                "common_absolute_test_distribution": False,
            },
        }

    rankings = {
        bank: sorted(
            CONDITION_ORDER,
            key=lambda condition: (
                -condition_stats[condition][bank]["mean_rate"],
                condition,
            ),
        )
        for bank in BANKS
    }
    rankings["balanced_descriptive_only"] = sorted(
        CONDITION_ORDER,
        key=lambda condition: (
            -condition_stats[condition]["balanced_descriptive_score"]["mean"],
            condition,
        ),
    )

    contrast_specs = {
        "start25_minus_start15": ("START25_APP6", "START15_APP6"),
        "start35_minus_start25": ("START35_APP6", "START25_APP6"),
        "start35_minus_start15": ("START35_APP6", "START15_APP6"),
        "approach_narrow_minus_reference": (
            "START25_APP3P6",
            "START25_APP6",
        ),
        "approach_wide_minus_reference": (
            "START25_APP8P4",
            "START25_APP6",
        ),
        "approach_narrow_minus_wide": (
            "START25_APP3P6",
            "START25_APP8P4",
        ),
    }
    canonical_deltas = {}
    for seed in CANONICAL_SEEDS:
        canonical_deltas[str(seed)] = {}
        for name, (left, right) in contrast_specs.items():
            canonical_deltas[str(seed)][name] = {
                bank: (
                    policies[policy_id(seed, left)][bank]["rate"]
                    - policies[policy_id(seed, right)][bank]["rate"]
                )
                for bank in BANKS
            }

    comparisons = {}
    bootstrap = {}
    for index, (name, (left, right)) in enumerate(contrast_specs.items()):
        comparisons[name] = {
            "left": left,
            "right": right,
            "absolute_state_pairing": (
                CONDITION_START_RADIUS[left] == CONDITION_START_RADIUS[right]
            ),
            "pairing_basis": (
                "identical absolute states and RNG"
                if CONDITION_START_RADIUS[left] == CONDITION_START_RADIUS[right]
                else "identical normalized quantile/direction and RNG; absolute states differ"
            ),
        }
        for bank_index, bank in enumerate(BANKS):
            values = [
                canonical_deltas[str(seed)][name][bank]
                for seed in CANONICAL_SEEDS
            ]
            comparisons[name][bank] = {
                "canonical_seed_deltas": values,
                "all_five_policy_level_mean": statistics.mean(values),
                "sample_std_ddof1": statistics.stdev(values),
            }
            bootstrap[f"{name}/{bank}"] = cluster_bootstrap(
                values, seed=202607250 + index * 2 + bank_index
            )

    sensitivity = {}
    for label, seeds in (
        ("canonical_seed1_3", (1, 2, 3)),
        ("alias_seed4_5", (4, 5)),
    ):
        sensitivity[label] = {}
        for name in contrast_specs:
            sensitivity[label][name] = {}
            for bank in BANKS:
                values = [
                    canonical_deltas[str(seed)][name][bank] for seed in seeds
                ]
                sensitivity[label][name][bank] = {
                    "canonical_seeds": list(seeds),
                    "values": values,
                    "mean": statistics.mean(values),
                }

    discordances = defaultdict(dict)
    for seed in CANONICAL_SEEDS:
        for bank in BANKS:
            for left, right in itertools.combinations(CONDITION_ORDER, 2):
                discordances[str(seed)][f"{bank}/{left}__vs__{right}"] = {
                    "pairing_basis": (
                        "absolute"
                        if CONDITION_START_RADIUS[left]
                        == CONDITION_START_RADIUS[right]
                        else "normalized"
                    ),
                    **paired_discordance(
                        policy_rows[policy_id(seed, left)][bank],
                        policy_rows[policy_id(seed, right)][bank],
                    ),
                }

    return {
        "schema_version": 1,
        "status": "valid",
        "experiment": "tro_stage2_position_axial_idood_rerollout",
        "definition_of_done_validation": {
            "checkpoints_revalidated": 25,
            "state_manifests": 30,
            "rollout_tasks": validated["validated_tasks"],
            "rollout_rows": validated["total_rows"],
            "policies": len(policies),
            "id_rows_per_policy": 125,
            "ood_rows_per_policy": 125,
            "same_start_absolute_pairing": True,
            "cross_start_normalized_pairing": True,
            "runtime_rng_pairing": True,
            "point_cloud_rng_pairing": True,
        },
        "independent_unit": "dataset-policy slot (canonical seed x condition)",
        "nested_trials": "five rollout seeds x 25 states per ID/OOD bank",
        "policies": policies,
        "conditions": condition_stats,
        "rankings": rankings,
        "pareto_front_id_ood": pareto_front(condition_stats),
        "canonical_seed_paired_deltas": canonical_deltas,
        "required_comparisons": comparisons,
        "canonical_seed_cluster_bootstrap": bootstrap,
        "seed_group_sensitivity": sensitivity,
        "paired_discordances": dict(discordances),
        "manifest_feasibility_and_radial_audit": validated["manifest_report"],
        "pairing_assertions": {
            "same_start": validated["same_start_assertions"],
            "cross_start": validated["cross_start_assertions"],
        },
        "source_condition_summaries": validated["source_summaries"],
        "limitations": [
            "ID and OOD refer only to geometric Start XZ support.",
            "Balanced scores are condition-relative descriptions, not performance on a common absolute test distribution.",
            "Cross-Start comparisons pair normalized radial quantile, direction and RNG; their absolute states differ.",
            "Wilson intervals describe rollout trials only; policy-level uncertainty uses canonical-seed cluster bootstrap.",
        ],
    }


def write_markdown(report):
    lines = [
        "# T-RO Stage 2 Position condition-relative ID/OOD rerollout",
        "",
        "Strict validation passed for 25 reused checkpoints, 30 frozen state "
        "manifests, 250/250 formal tasks and 6,250/6,250 rollout rows. Every "
        "policy has exactly 125 ID and 125 OOD trials.",
        "",
        "## Policy results",
        "",
        "| Seed | Actual collection/training | Condition | ID | OOD | "
        "OOD − ID | Balanced (descriptive) |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for seed in CANONICAL_SEEDS:
        for condition in CONDITION_ORDER:
            row = report["policies"][policy_id(seed, condition)]
            lines.append(
                f"| {seed} | {row['source_collection_seed']}/"
                f"{row['source_training_seed']} | `{condition}` | "
                f"{row['id']['successes']}/125 ({row['id']['rate']:.3f}) | "
                f"{row['ood']['successes']}/125 ({row['ood']['rate']:.3f}) | "
                f"{row['generalisation_gap_ood_minus_id']:+.3f} | "
                f"{row['balanced_descriptive_score']:.3f} |"
            )
    lines.extend(
        [
            "",
            "## Condition-level ID/OOD trade-off",
            "",
            "| Condition | ID mean ± policy std | OOD mean ± policy std | "
            "Gap mean ± policy std | Pareto |",
            "|---|---:|---:|---:|---|",
        ]
    )
    pareto = set(report["pareto_front_id_ood"])
    for condition in CONDITION_ORDER:
        row = report["conditions"][condition]
        lines.append(
            f"| `{condition}` | {row['id']['mean_rate']:.3f} ± "
            f"{row['id']['sample_std_rate_ddof1']:.3f} | "
            f"{row['ood']['mean_rate']:.3f} ± "
            f"{row['ood']['sample_std_rate_ddof1']:.3f} | "
            f"{row['generalisation_gap_ood_minus_id']['mean']:+.3f} ± "
            f"{row['generalisation_gap_ood_minus_id']['sample_std_ddof1']:.3f} | "
            f"{'yes' if condition in pareto else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"ID ranking: `{report['rankings']['id']}`.",
            "",
            f"OOD ranking: `{report['rankings']['ood']}`.",
            "",
            f"ID/OOD Pareto front: `{report['pareto_front_id_ood']}`.",
            "",
            "The balanced ranking in `comparison.json` is descriptive only. "
            "Its banks have different absolute radial intervals across Start "
            "families and therefore do not form a common deployment distribution.",
            "",
            "## Pairing and uncertainty",
            "",
            "The three `START25_*` conditions use identical absolute states, "
            "state order and RNG streams. Cross-Start comparisons use identical "
            "area quantiles, XZ directions, normalized state indices and RNG "
            "streams, while absolute positions necessarily differ.",
            "",
            "Wilson intervals are rollout-level descriptions only. The cluster "
            "bootstrap resamples the five canonical dataset-policy seeds as "
            "top-level policy units.",
            "",
        ]
    )
    (ANALYSIS / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def plot(report):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = ANALYSIS / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    labels = list(CONDITION_ORDER)
    x = np.arange(len(labels))
    width = 0.36
    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    for offset, bank, color in (
        (-width / 2, "id", "#2563EB"),
        (width / 2, "ood", "#EA580C"),
    ):
        axis.bar(
            x + offset,
            [report["conditions"][name][bank]["mean_rate"] for name in labels],
            width,
            yerr=[
                report["conditions"][name][bank]["sample_std_rate_ddof1"]
                for name in labels
            ],
            capsize=3,
            label=bank.upper(),
            color=color,
        )
    axis.set_xticks(x, labels, rotation=20, ha="right")
    axis.set_ylabel("Success rate")
    axis.set_ylim(0.0, 1.0)
    axis.set_title("Condition-relative ID/OOD mean ± policy sample std")
    axis.grid(axis="y", alpha=0.25)
    axis.legend()
    fig.savefig(figures / "condition_id_ood_tradeoff.png", dpi=180)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(7, 6), constrained_layout=True)
    for condition in labels:
        row = report["conditions"][condition]
        axis.scatter(
            row["id"]["mean_rate"],
            row["ood"]["mean_rate"],
            s=90,
            label=condition,
        )
        axis.annotate(
            condition,
            (row["id"]["mean_rate"], row["ood"]["mean_rate"]),
            xytext=(5, 4),
            textcoords="offset points",
            fontsize=8,
        )
    axis.set_xlabel("Condition-relative ID success rate")
    axis.set_ylabel("Condition-relative OOD success rate")
    axis.set_xlim(0.0, 1.0)
    axis.set_ylim(0.0, 1.0)
    axis.grid(alpha=0.25)
    fig.savefig(figures / "id_ood_pareto.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for axis, bank in zip(axes, BANKS):
        for radius in START_RADII:
            values = []
            for seed in ROLLOUT_SEEDS:
                payload = read_json(manifest_path(radius, seed, bank))
                values.extend(
                    row["radial_distance_from_center"]
                    for row in payload["shared_start_records"]
                )
            axis.hist(values, bins=15, alpha=0.45, label=f"R={radius:.2f}")
        axis.set_title(bank.upper())
        axis.set_xlabel("Realised target radial distance (m)")
        axis.set_ylabel("State count")
        axis.legend()
    fig.savefig(figures / "realised_radial_distributions.png", dpi=180)
    plt.close(fig)


def write_merge_validation(validated):
    payload = {
        "schema_version": 1,
        "status": "valid",
        "validated_tasks": validated["validated_tasks"],
        "validated_rows": validated["total_rows"],
        "policies": 25,
        "id_rows_per_policy": 125,
        "ood_rows_per_policy": 125,
        "same_start_absolute_pairing": True,
        "cross_start_normalized_pairing": True,
        "checkpoint_hashes": "revalidated",
        "source_summaries": validated["source_summaries"],
    }
    write_json(MANIFESTS / "merge_validation.json", payload)
    return payload


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    for path, expected in OLD_ANALYSIS.items():
        if sha256(path) != expected:
            raise ValueError(f"Original Stage 2 analysis changed: {path}")
    validated = validate_and_collect()
    merge = write_merge_validation(validated)
    if args.validate_only:
        print(json.dumps(merge, indent=2))
        return
    report = summarize(validated)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    write_json(ANALYSIS / "comparison.json", report)
    write_markdown(report)
    plot(report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "tasks": report["definition_of_done_validation"][
                    "rollout_tasks"
                ],
                "rows": report["definition_of_done_validation"]["rollout_rows"],
                "pareto": report["pareto_front_id_ood"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
