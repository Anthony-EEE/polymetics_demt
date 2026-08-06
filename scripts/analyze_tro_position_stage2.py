#!/usr/bin/env python3
"""Strict validation and pre-registered analysis for T-RO Stage 2 Position."""

import hashlib
import itertools
import json
import math
import re
import statistics
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "tro_stage2_position_axial_replication"
MANIFESTS = EXPERIMENT / "manifests"
ANALYSIS = EXPERIMENT / "analysis"
ROLLOUT_ROOT = ROOT / "dataset" / "tro_position_stage2_axial" / "rollouts" / "formal"
CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP6",
    "START25_APP8P4",
)
CANONICAL_SEEDS = (1, 2, 3, 4, 5)
ROLLOUT_SEEDS = (1, 2, 3, 4, 5)
BANKS = ("inner", "outer")
DELTA_MIN = 0.05


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(successes, total, z=1.959963984540054):
    rate = successes / total
    denominator = 1.0 + z * z / total
    center = (rate + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(
        rate * (1.0 - rate) / total + z * z / (4.0 * total * total)
    ) / denominator
    return [center - margin, center + margin]


def stats(rows):
    successes = sum(bool(row["success"]) for row in rows)
    total = len(rows)
    return {
        "successes": successes,
        "total": total,
        "rate": successes / total,
        "wilson_95": wilson(successes, total),
    }


def policy_id(canonical_seed, condition):
    return f"seed{canonical_seed}/{condition}"


def assert_exact_latent_pairing():
    datasets = read_json(MANIFESTS / "datasets.json")["datasets"]
    by_key = {
        (int(row["canonical_seed"]), row["condition"]): row for row in datasets
    }
    assertions = {}
    for canonical_seed in CANONICAL_SEEDS:
        ids = [
            by_key[(canonical_seed, condition)]["canonical_candidate_ids"]
            for condition in CONDITIONS
        ]
        exact = all(value == ids[0] for value in ids[1:]) and len(ids[0]) == 30
        if not exact:
            raise ValueError(
                f"Canonical seed {canonical_seed} lacks exact five-condition "
                "accepted-latent pairing"
            )
        assertions[str(canonical_seed)] = {
            "exact": True,
            "accepted_candidate_ids": ids[0],
        }
    return assertions


def validate_and_collect():
    unified_path = MANIFESTS / "checkpoints.json"
    unified = read_json(unified_path)
    if unified.get("frozen_before_rollout") is not True:
        raise ValueError("Checkpoints were not declared frozen before rollout")
    if len(unified["checkpoints"]) != 25:
        raise ValueError("Expected 25 unified checkpoint rows")
    checkpoint_by_key = {}
    for record in unified["checkpoints"]:
        key = (int(record["canonical_seed"]), record["condition"])
        checkpoint = Path(record["checkpoint_path"])
        if sha256(checkpoint) != record["checkpoint_sha256"]:
            raise ValueError(f"{key}: checkpoint hash mismatch")
        if not record["reused_policy"]:
            epochs = [int(row["epoch"]) for row in record["available_checkpoints"]]
            if int(record["epoch"]) != max(epochs):
                raise ValueError(f"{key}: checkpoint is not highest emitted epoch")
        checkpoint_by_key[key] = record

    expected_tasks = len(CANONICAL_SEEDS) * len(CONDITIONS) * len(
        ROLLOUT_SEEDS
    ) * len(BANKS)
    policy_rows = {
        policy_id(seed, condition): {}
        for seed in CANONICAL_SEEDS
        for condition in CONDITIONS
    }
    source_summaries = []
    validated_tasks = 0
    for canonical_seed in CANONICAL_SEEDS:
        checkpoint_view_path = MANIFESTS / f"checkpoints_seed{canonical_seed}.json"
        checkpoint_view = read_json(checkpoint_view_path)
        if checkpoint_view["condition_order"] != list(CONDITIONS):
            raise ValueError(f"seed{canonical_seed}: checkpoint condition order")
        if checkpoint_view["unified_checkpoint_manifest_sha256"] != sha256(
            unified_path
        ):
            raise ValueError(f"seed{canonical_seed}: unified checkpoint hash")
        for rollout_seed in ROLLOUT_SEEDS:
            for bank in BANKS:
                bank_id = f"tro_stage2_seed{rollout_seed}_{bank}_n25_v1"
                start_path = MANIFESTS / "rollout_5seed" / f"{bank_id}.json"
                start = read_json(start_path)
                if int(start["seed"]) != rollout_seed:
                    raise ValueError(f"{bank_id}: rollout seed mismatch")
                if int(start["num_rollouts"]) != 25:
                    raise ValueError(f"{bank_id}: state count mismatch")
                expected_records = start["shared_start_records"]
                expected_ids = [row["state_id"] for row in expected_records]
                if len(expected_ids) != 25 or len(set(expected_ids)) != 25:
                    raise ValueError(f"{bank_id}: invalid state IDs")
                radii = [
                    float(row["radial_distance_from_center"])
                    for row in expected_records
                ]
                if bank == "inner" and not all(
                    0.0 <= radius <= 0.25 for radius in radii
                ):
                    raise ValueError(f"{bank_id}: inner radius violation")
                if bank == "outer" and not all(
                    0.25 < radius <= 0.35 for radius in radii
                ):
                    raise ValueError(f"{bank_id}: outer radius violation")
                summary_path = (
                    ROLLOUT_ROOT
                    / f"seed{canonical_seed}"
                    / f"rollout_seed{rollout_seed}"
                    / bank
                    / f"summary_seed{rollout_seed}_n25.json"
                )
                aggregate = read_json(summary_path)
                source_summaries.append(str(summary_path.resolve()))
                if aggregate["condition_order"] != list(CONDITIONS):
                    raise ValueError(f"{summary_path}: condition order")
                if aggregate["bank_id"] != bank_id:
                    raise ValueError(f"{summary_path}: bank ID")
                if aggregate["start_manifest_sha256"] != sha256(start_path):
                    raise ValueError(f"{summary_path}: start manifest hash")
                if aggregate["checkpoint_manifest_sha256"] != sha256(
                    checkpoint_view_path
                ):
                    raise ValueError(f"{summary_path}: checkpoint view hash")
                summaries = {
                    row["condition"]: row for row in aggregate["summaries"]
                }
                if tuple(summaries) != CONDITIONS:
                    raise ValueError(f"{summary_path}: condition summaries")
                for condition in CONDITIONS:
                    summary = summaries[condition]
                    checkpoint = checkpoint_by_key[(canonical_seed, condition)]
                    if summary["checkpoint"] != checkpoint["checkpoint_path"]:
                        raise ValueError(
                            f"seed{canonical_seed}/{condition}: checkpoint path"
                        )
                    if summary["checkpoint_sha256"] != checkpoint[
                        "checkpoint_sha256"
                    ]:
                        raise ValueError(
                            f"seed{canonical_seed}/{condition}: checkpoint hash"
                        )
                    if int(summary["block"]) != canonical_seed:
                        raise ValueError(
                            f"seed{canonical_seed}/{condition}: canonical alias"
                        )
                    rows = summary["rollouts"]
                    if len(rows) != 25:
                        raise ValueError(
                            f"seed{canonical_seed}/{condition}/{bank_id}: rows"
                        )
                    if [row["state_id"] for row in rows] != expected_ids:
                        raise ValueError(
                            f"seed{canonical_seed}/{condition}/{bank_id}: state order"
                        )
                    for index, row in enumerate(rows):
                        expected = expected_records[index]
                        if row["paired_spec"] != expected:
                            raise ValueError(
                                f"seed{canonical_seed}/{condition}/{bank_id}: "
                                "state/RNG specification"
                            )
                        if int(row["rng_seed"]) != int(expected["rng_seed"]):
                            raise ValueError("Runtime RNG mismatch")
                        if int(row["point_cloud_rng_seed"]) != int(
                            expected["point_cloud_rng_seed"]
                        ):
                            raise ValueError("Point-cloud RNG mismatch")
                        if row["checkpoint_sha256"] != checkpoint[
                            "checkpoint_sha256"
                        ]:
                            raise ValueError("Rollout-row checkpoint mismatch")
                        key = f"rollout_seed{rollout_seed}/{bank}/{row['state_id']}"
                        pid = policy_id(canonical_seed, condition)
                        if key in policy_rows[pid]:
                            raise ValueError(f"{pid}: duplicate trial {key}")
                        policy_rows[pid][key] = row
                    validated_tasks += 1
    if validated_tasks != expected_tasks:
        raise ValueError(
            f"Expected {expected_tasks} tasks, validated {validated_tasks}"
        )
    expected_keys = set(next(iter(policy_rows.values())))
    if len(expected_keys) != 250:
        raise ValueError(f"Expected 250 trials per policy, got {len(expected_keys)}")
    for pid, rows in policy_rows.items():
        if set(rows) != expected_keys:
            raise ValueError(f"{pid}: deployment trials are not exactly paired")
    total_rows = sum(len(rows) for rows in policy_rows.values())
    if total_rows != 6250:
        raise ValueError(f"Expected 6,250 rows, got {total_rows}")
    latent_pairing = assert_exact_latent_pairing()
    return (
        policy_rows,
        checkpoint_by_key,
        source_summaries,
        latent_pairing,
        validated_tasks,
    )


def validation_history(checkpoint):
    run_dir = Path(
        checkpoint.get(
            "run_dir",
            Path(checkpoint["checkpoint_path"]).parents[1],
        )
    )
    log_path = run_dir / "logs" / "log.txt"
    history = []
    if not log_path.is_file():
        return {
            "available": False,
            "log_path": str(log_path),
            "epochs": history,
        }
    current_epoch = None
    epoch_pattern = re.compile(r"Validation Epoch\s+(\d+)")
    loss_pattern = re.compile(r'"Loss":\s*([-+0-9.eE]+)')
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        epoch_match = epoch_pattern.search(line)
        if epoch_match:
            current_epoch = int(epoch_match.group(1))
            continue
        loss_match = loss_pattern.search(line)
        if loss_match and current_epoch is not None:
            history.append(
                {"epoch": current_epoch, "loss": float(loss_match.group(1))}
            )
            current_epoch = None
    return {
        "available": bool(history),
        "log_path": str(log_path.resolve()),
        "log_sha256": sha256(log_path),
        "epochs": history,
    }


def paired_discordances(policy_rows, canonical_seed):
    tables = {}
    shared_keys = sorted(
        policy_rows[policy_id(canonical_seed, CONDITIONS[0])]
    )
    for left, right in itertools.combinations(CONDITIONS, 2):
        pairs = [
            (
                bool(policy_rows[policy_id(canonical_seed, left)][key]["success"]),
                bool(policy_rows[policy_id(canonical_seed, right)][key]["success"]),
            )
            for key in shared_keys
        ]
        tables[f"{left}__vs__{right}"] = {
            "both_success": sum(a and b for a, b in pairs),
            f"{left}_only": sum(a and not b for a, b in pairs),
            f"{right}_only": sum((not a) and b for a, b in pairs),
            "both_failure": sum((not a) and (not b) for a, b in pairs),
        }
    return tables


def contrast_pass(values):
    return {
        "mean_delta": statistics.mean(values),
        "positive_slots": sum(value > 0.0 for value in values),
        "required_mean_delta": DELTA_MIN,
        "required_positive_slots": 4,
        "passed": (
            statistics.mean(values) >= DELTA_MIN
            and sum(value > 0.0 for value in values) >= 4
        ),
    }


def cluster_bootstrap(delta_by_seed, draws=100000, seed=20260725):
    rng = np.random.default_rng(seed)
    values = np.asarray(delta_by_seed, dtype=float)
    samples = rng.choice(values, size=(draws, len(values)), replace=True).mean(axis=1)
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
        "probability_mean_ge_delta_min": float(np.mean(samples >= DELTA_MIN)),
    }


def classify(primary_reference, primary_wide, rankings):
    if (
        primary_reference["passed"]
        and primary_wide["passed"]
        and rankings["combined"][0] == "START25_APP3P6"
    ):
        return "strong"
    if primary_reference["passed"] or primary_wide["passed"]:
        return "partial"
    return "null/unstable"


def summarize(
    policy_rows,
    checkpoint_by_key,
    source_summaries,
    latent_pairing,
    validated_tasks,
):
    policies = {}
    for canonical_seed in CANONICAL_SEEDS:
        for condition in CONDITIONS:
            pid = policy_id(canonical_seed, condition)
            keyed = policy_rows[pid]
            per_seed = {}
            for rollout_seed in ROLLOUT_SEEDS:
                per_seed[str(rollout_seed)] = {}
                for bank in BANKS:
                    per_seed[str(rollout_seed)][bank] = stats(
                        [
                            row
                            for key, row in keyed.items()
                            if key.startswith(f"rollout_seed{rollout_seed}/{bank}/")
                        ]
                    )
                per_seed[str(rollout_seed)]["combined"] = stats(
                    [
                        row
                        for key, row in keyed.items()
                        if key.startswith(f"rollout_seed{rollout_seed}/")
                    ]
                )
            checkpoint = checkpoint_by_key[(canonical_seed, condition)]
            policy = {
                "canonical_seed": canonical_seed,
                "source_collection_seed": checkpoint["source_collection_seed"],
                "source_training_seed": checkpoint["source_training_seed"],
                "condition": condition,
                "checkpoint": {
                    "epoch": checkpoint["epoch"],
                    "path": checkpoint["checkpoint_path"],
                    "sha256": checkpoint["checkpoint_sha256"],
                    "reused_policy": checkpoint["reused_policy"],
                },
                "validation_history": validation_history(checkpoint),
                "combined": stats(list(keyed.values())),
                "inner": stats(
                    [row for key, row in keyed.items() if "/inner/" in key]
                ),
                "outer": stats(
                    [row for key, row in keyed.items() if "/outer/" in key]
                ),
                "per_rollout_seed": per_seed,
                "rollout_seed_mean_and_sample_std": {},
            }
            for scope in ("combined", "inner", "outer"):
                rates = [
                    per_seed[str(seed)][scope]["rate"] for seed in ROLLOUT_SEEDS
                ]
                policy["rollout_seed_mean_and_sample_std"][scope] = {
                    "seed_rates": rates,
                    "mean_rate": statistics.mean(rates),
                    "sample_std_rate_ddof1": statistics.stdev(rates),
                }
            policies[pid] = policy

    conditions = {}
    for condition in CONDITIONS:
        conditions[condition] = {}
        for scope in ("combined", "inner", "outer"):
            rates = [
                policies[policy_id(seed, condition)][scope]["rate"]
                for seed in CANONICAL_SEEDS
            ]
            conditions[condition][scope] = {
                "policy_rates": rates,
                "mean_rate": statistics.mean(rates),
                "sample_std_rate_ddof1": statistics.stdev(rates),
            }
    rankings = {
        scope: sorted(
            CONDITIONS,
            key=lambda condition: (
                -conditions[condition][scope]["mean_rate"],
                condition,
            ),
        )
        for scope in ("combined", "inner", "outer")
    }
    deltas = {}
    for canonical_seed in CANONICAL_SEEDS:
        def rate(condition, scope):
            return policies[policy_id(canonical_seed, condition)][scope]["rate"]

        deltas[str(canonical_seed)] = {
            "D_candidate_reference": (
                rate("START25_APP3P6", "combined")
                - rate("START25_APP6", "combined")
            ),
            "D_candidate_wide": (
                rate("START25_APP3P6", "combined")
                - rate("START25_APP8P4", "combined")
            ),
            "D_start_outer": (
                rate("START35_APP6", "outer")
                - rate("START15_APP6", "outer")
            ),
            "D_approach_inner": (
                rate("START25_APP3P6", "inner")
                - rate("START25_APP8P4", "inner")
            ),
        }
    reference_values = [
        deltas[str(seed)]["D_candidate_reference"] for seed in CANONICAL_SEEDS
    ]
    wide_values = [
        deltas[str(seed)]["D_candidate_wide"] for seed in CANONICAL_SEEDS
    ]
    primary_reference = contrast_pass(reference_values)
    primary_wide = contrast_pass(wide_values)
    classification = classify(primary_reference, primary_wide, rankings)
    sensitivity = {}
    for name, seeds in (
        ("fresh_canonical_seed1_3", (1, 2, 3)),
        ("reused_alias_seed4_5", (4, 5)),
    ):
        sensitivity[name] = {
            contrast: {
                "canonical_seeds": list(seeds),
                "values": [deltas[str(seed)][contrast] for seed in seeds],
                "mean_delta": statistics.mean(
                    deltas[str(seed)][contrast] for seed in seeds
                ),
                "positive_slots": sum(
                    deltas[str(seed)][contrast] > 0.0 for seed in seeds
                ),
            }
            for contrast in ("D_candidate_reference", "D_candidate_wide")
        }
    return {
        "schema_version": 1,
        "status": "valid",
        "classification": classification,
        "definition_of_done_validation": {
            "rollout_tasks": validated_tasks,
            "expected_rollout_tasks": 250,
            "rollout_rows": sum(len(rows) for rows in policy_rows.values()),
            "expected_rollout_rows": 6250,
            "policies": len(policies),
            "exact_latent_pairing": True,
        },
        "independent_unit": "dataset-policy slot (canonical seed x condition)",
        "nested_trials": "five rollout seeds x inner/outer deployment states",
        "conditions": conditions,
        "policies": policies,
        "canonical_seed_deltas": deltas,
        "primary_contrasts": {
            "D_candidate_reference": {
                "slot_values": reference_values,
                **primary_reference,
            },
            "D_candidate_wide": {
                "slot_values": wide_values,
                **primary_wide,
            },
        },
        "rankings": rankings,
        "paired_discordances_by_canonical_seed": {
            str(seed): paired_discordances(policy_rows, seed)
            for seed in CANONICAL_SEEDS
        },
        "policy_level_cluster_bootstrap": {
            "D_candidate_reference": cluster_bootstrap(
                reference_values, seed=202607251
            ),
            "D_candidate_wide": cluster_bootstrap(
                wide_values, seed=202607252
            ),
        },
        "sensitivity": sensitivity,
        "exact_latent_pairing_assertion": latent_pairing,
        "source_aggregate_summaries": source_summaries,
    }


def write_markdown(report):
    lines = [
        "# T-RO Stage 2 Position axial replication",
        "",
        f"**Classification: `{report['classification']}`.**",
        "",
        "Strict validation passed for 25 dataset-policy slots, 250/250 formal "
        "policy/rollout-seed/bank tasks and 6,250/6,250 rollout rows. Every "
        "canonical slot has exact five-condition accepted-latent pairing.",
        "",
        "## Policy results",
        "",
        "| Canonical seed | Actual collection/training seed | Condition | "
        "Successes/250 | Five rollout seeds mean ± sample std | Checkpoint epoch |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for canonical_seed in CANONICAL_SEEDS:
        for condition in CONDITIONS:
            row = report["policies"][policy_id(canonical_seed, condition)]
            combined = row["rollout_seed_mean_and_sample_std"]["combined"]
            lines.append(
                f"| {canonical_seed} | {row['source_collection_seed']}/"
                f"{row['source_training_seed']} | `{condition}` | "
                f"{row['combined']['successes']}/250 | "
                f"{combined['mean_rate']:.3f} ± "
                f"{combined['sample_std_rate_ddof1']:.3f} | "
                f"{row['checkpoint']['epoch']} |"
            )
    lines.extend(
        [
            "",
            "## Condition-level policy replication",
            "",
            "| Rank | Condition | Five policy rates | Mean ± sample std |",
            "|---:|---|---|---:|",
        ]
    )
    for rank, condition in enumerate(report["rankings"]["combined"], 1):
        row = report["conditions"][condition]["combined"]
        lines.append(
            f"| {rank} | `{condition}` | "
            f"`{[round(value, 3) for value in row['policy_rates']]}` | "
            f"{row['mean_rate']:.3f} ± {row['sample_std_rate_ddof1']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Canonical-seed deltas",
            "",
            "| Seed | Candidate − reference | Candidate − wide | "
            "Start outer wide − tight | Approach inner tight − wide |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for canonical_seed in CANONICAL_SEEDS:
        row = report["canonical_seed_deltas"][str(canonical_seed)]
        lines.append(
            f"| {canonical_seed} | {row['D_candidate_reference']:+.3f} | "
            f"{row['D_candidate_wide']:+.3f} | "
            f"{row['D_start_outer']:+.3f} | "
            f"{row['D_approach_inner']:+.3f} |"
        )
    lines.extend(["", "## Pre-registered decision", ""])
    for name, row in report["primary_contrasts"].items():
        lines.append(
            f"- `{name}`: mean `{row['mean_delta']:+.3f}`, "
            f"{row['positive_slots']}/5 positive slots, passed=`{row['passed']}`."
        )
    lines.extend(
        [
            "",
            f"Combined ranking: `{report['rankings']['combined']}`.",
            "",
            f"Inner ranking: `{report['rankings']['inner']}`.",
            "",
            f"Outer ranking: `{report['rankings']['outer']}`.",
            "",
            "Wilson intervals in `comparison.json` are rollout-level descriptive "
            "intervals only. The cluster bootstrap resamples canonical dataset-policy "
            "slots as the top-level units. Rollout seeds are nested deployment "
            "trials, not independently trained policies.",
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
    labels = list(CONDITIONS)
    means = [report["conditions"][name]["combined"]["mean_rate"] for name in labels]
    stds = [
        report["conditions"][name]["combined"]["sample_std_rate_ddof1"]
        for name in labels
    ]
    fig, axis = plt.subplots(figsize=(11, 5), constrained_layout=True)
    axis.bar(range(len(labels)), means, yerr=stds, capsize=4, color="#3B82F6")
    axis.set_xticks(range(len(labels)), labels, rotation=20, ha="right")
    axis.set_ylabel("Combined success rate")
    axis.set_title("Stage 2 mean ± sample std across five policies")
    axis.set_ylim(0.0, 1.0)
    axis.grid(axis="y", alpha=0.25)
    fig.savefig(figures / "condition_policy_replication.png", dpi=180)
    plt.close(fig)

    seeds = list(CANONICAL_SEEDS)
    reference = [
        report["canonical_seed_deltas"][str(seed)]["D_candidate_reference"]
        for seed in seeds
    ]
    wide = [
        report["canonical_seed_deltas"][str(seed)]["D_candidate_wide"]
        for seed in seeds
    ]
    x = np.arange(len(seeds))
    width = 0.36
    fig, axis = plt.subplots(figsize=(9, 5), constrained_layout=True)
    axis.bar(x - width / 2, reference, width, label="Candidate − reference")
    axis.bar(x + width / 2, wide, width, label="Candidate − wide")
    axis.axhline(0.0, color="black", linewidth=1)
    axis.axhline(DELTA_MIN, color="#DC2626", linestyle="--", label="δ min = 0.05")
    axis.set_xticks(x, [f"seed{seed}" for seed in seeds])
    axis.set_ylabel("Combined success-rate delta")
    axis.set_title("Pre-registered primary contrasts by dataset-policy slot")
    axis.legend()
    axis.grid(axis="y", alpha=0.25)
    fig.savefig(figures / "primary_contrasts_by_seed.png", dpi=180)
    plt.close(fig)


def main():
    validated = validate_and_collect()
    report = summarize(*validated)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    write_json(ANALYSIS / "comparison.json", report)
    write_markdown(report)
    plot(report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "classification": report["classification"],
                "rollout_tasks": report["definition_of_done_validation"][
                    "rollout_tasks"
                ],
                "rollout_rows": report["definition_of_done_validation"][
                    "rollout_rows"
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
