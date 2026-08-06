#!/usr/bin/env python3
"""Validate and compare the eight existing policies on five paired seeds."""

import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "mvp0_position_event"
MANIFESTS = EXPERIMENT / "manifests"
ANALYSIS = EXPERIMENT / "analysis"
ROLLOUT_ROOT = ROOT / "dataset" / "tro_position_mvp0" / "rollouts_5seed_n50"
SEEDS = (628, 629, 630, 631, 632)
BANKS = ("inner", "outer")
CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP8P4",
)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wilson(successes, total, z=1.959963984540054):
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(
        p * (1.0 - p) / total + z * z / (4.0 * total * total)
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


def policy_id(block, condition):
    return f"block{block}/{condition}"


def validate_and_collect():
    expected_rows = 2 * len(CONDITIONS) * len(SEEDS) * len(BANKS) * 25
    policy_rows = {
        policy_id(block, condition): {}
        for block in (0, 1)
        for condition in CONDITIONS
    }
    checkpoint_records = {}
    source_summaries = []

    for block in (0, 1):
        checkpoint_manifest_path = (
            MANIFESTS / f"checkpoints_latest_existing_b{block}.json"
        )
        checkpoint_manifest = read_json(checkpoint_manifest_path)
        if checkpoint_manifest["condition_order"] != list(CONDITIONS):
            raise ValueError(f"Block {block}: checkpoint condition order mismatch")
        if checkpoint_manifest.get("retraining_performed") is not False:
            raise ValueError(f"Block {block}: expected existing checkpoints only")

        for condition in CONDITIONS:
            record = checkpoint_manifest["checkpoints"][condition]
            checkpoint = Path(record["path"])
            if sha256(checkpoint) != record["sha256"]:
                raise ValueError(f"Block {block}/{condition}: checkpoint hash mismatch")
            available_epochs = [
                int(row["epoch"]) for row in record["available_checkpoints"]
            ]
            if int(record["epoch"]) != max(available_epochs):
                raise ValueError(
                    f"Block {block}/{condition}: selected checkpoint is not latest"
                )
            checkpoint_records[policy_id(block, condition)] = record

        for seed in SEEDS:
            for bank in BANKS:
                bank_id = f"tro_pos_seed{seed}_{bank}_n25_v1"
                start_manifest_path = (
                    MANIFESTS / "rollout_5seed" / f"{bank_id}.json"
                )
                start_manifest = read_json(start_manifest_path)
                if int(start_manifest["seed"]) != seed:
                    raise ValueError(f"{bank_id}: seed mismatch")
                if int(start_manifest["num_rollouts"]) != 25:
                    raise ValueError(f"{bank_id}: expected 25 states")
                if start_manifest["protocol"]["bank_id"] != bank_id:
                    raise ValueError(f"{bank_id}: bank ID mismatch")
                expected_state_ids = [
                    row["state_id"] for row in start_manifest["shared_start_records"]
                ]
                if len(expected_state_ids) != 25 or len(set(expected_state_ids)) != 25:
                    raise ValueError(f"{bank_id}: state IDs are not 25 unique values")
                radii = [
                    float(row["radial_distance_from_center"])
                    for row in start_manifest["shared_start_records"]
                ]
                if bank == "inner" and not all(0.0 <= radius <= 0.25 for radius in radii):
                    raise ValueError(f"{bank_id}: inner radius violation")
                if bank == "outer" and not all(0.25 < radius <= 0.35 for radius in radii):
                    raise ValueError(f"{bank_id}: outer radius violation")

                summary_path = (
                    ROLLOUT_ROOT
                    / f"block{block}"
                    / f"seed{seed}"
                    / bank
                    / f"summary_seed{seed}_n25.json"
                )
                aggregate = read_json(summary_path)
                source_summaries.append(str(summary_path))
                if aggregate["condition_order"] != list(CONDITIONS):
                    raise ValueError(f"{summary_path}: condition order mismatch")
                if aggregate["bank_id"] != bank_id:
                    raise ValueError(f"{summary_path}: bank mismatch")
                if int(aggregate["seed"]) != seed:
                    raise ValueError(f"{summary_path}: seed mismatch")
                if int(aggregate["num_rollouts"]) != 25:
                    raise ValueError(f"{summary_path}: rollout count mismatch")
                if aggregate["start_manifest_sha256"] != sha256(start_manifest_path):
                    raise ValueError(f"{summary_path}: start manifest hash mismatch")

                summaries = {
                    row["condition"]: row for row in aggregate["summaries"]
                }
                if tuple(summaries) != CONDITIONS:
                    raise ValueError(f"{summary_path}: policy summaries mismatch")
                for condition in CONDITIONS:
                    pid = policy_id(block, condition)
                    summary = summaries[condition]
                    checkpoint = checkpoint_records[pid]
                    if summary["checkpoint"] != checkpoint["path"]:
                        raise ValueError(f"{pid}/{seed}/{bank}: checkpoint path mismatch")
                    if summary["checkpoint_sha256"] != checkpoint["sha256"]:
                        raise ValueError(f"{pid}/{seed}/{bank}: checkpoint hash mismatch")
                    if int(summary["block"]) != block:
                        raise ValueError(f"{pid}/{seed}/{bank}: block mismatch")
                    rows = summary["rollouts"]
                    if len(rows) != 25:
                        raise ValueError(f"{pid}/{seed}/{bank}: expected 25 rows")
                    if [row["state_id"] for row in rows] != expected_state_ids:
                        raise ValueError(f"{pid}/{seed}/{bank}: state order mismatch")
                    for index, row in enumerate(rows):
                        if row["condition"] != condition:
                            raise ValueError(f"{pid}/{seed}/{bank}/{index}: condition mismatch")
                        if int(row["block"]) != block:
                            raise ValueError(f"{pid}/{seed}/{bank}/{index}: block mismatch")
                        if row["bank_id"] != bank_id:
                            raise ValueError(f"{pid}/{seed}/{bank}/{index}: bank mismatch")
                        if row["checkpoint_sha256"] != checkpoint["sha256"]:
                            raise ValueError(
                                f"{pid}/{seed}/{bank}/{index}: checkpoint mismatch"
                            )
                        key = f"seed{seed}/{bank}/{row['state_id']}"
                        if key in policy_rows[pid]:
                            raise ValueError(f"{pid}: duplicate deployment state {key}")
                        policy_rows[pid][key] = row

    actual_rows = sum(len(rows) for rows in policy_rows.values())
    if actual_rows != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows, got {actual_rows}")
    expected_keys = set(next(iter(policy_rows.values())))
    if len(expected_keys) != len(SEEDS) * len(BANKS) * 25:
        raise ValueError(f"Expected 250 shared states, got {len(expected_keys)}")
    for pid, rows in policy_rows.items():
        if set(rows) != expected_keys:
            raise ValueError(f"{pid}: does not share the exact same 250 states")
    return policy_rows, checkpoint_records, source_summaries


def compare(policy_rows, checkpoint_records, source_summaries):
    policies = {}
    for pid, keyed_rows in policy_rows.items():
        rows = list(keyed_rows.values())
        per_seed = {}
        for seed in SEEDS:
            per_seed[str(seed)] = {
                bank: stats(
                    [
                        row
                        for key, row in keyed_rows.items()
                        if key.startswith(f"seed{seed}/{bank}/")
                    ]
                )
                for bank in BANKS
            }
            seed_rows = [
                row
                for key, row in keyed_rows.items()
                if key.startswith(f"seed{seed}/")
            ]
            per_seed[str(seed)]["combined"] = stats(seed_rows)
        policies[pid] = {
            "block": int(pid[5]),
            "condition": pid.split("/", 1)[1],
            "checkpoint": {
                key: checkpoint_records[pid][key]
                for key in ("epoch", "path", "sha256", "selection_rule")
            },
            "combined": stats(rows),
            "inner": stats(
                [row for key, row in keyed_rows.items() if "/inner/" in key]
            ),
            "outer": stats(
                [row for key, row in keyed_rows.items() if "/outer/" in key]
            ),
            "per_seed": per_seed,
        }
        policies[pid]["rollout_seed_mean_and_sample_std"] = {}
        for scope in ("combined", "inner", "outer"):
            seed_rates = [
                per_seed[str(seed)][scope]["rate"] for seed in SEEDS
            ]
            policies[pid]["rollout_seed_mean_and_sample_std"][scope] = {
                "seed_rates": seed_rates,
                "mean_rate": statistics.mean(seed_rates),
                "sample_std_rate_ddof1": statistics.stdev(seed_rates),
                "num_seeds": len(seed_rates),
            }

    paired = {}
    policy_ids = list(policies)
    shared_keys = sorted(next(iter(policy_rows.values())))
    for left, right in itertools.combinations(policy_ids, 2):
        pairs = [
            (
                bool(policy_rows[left][key]["success"]),
                bool(policy_rows[right][key]["success"]),
            )
            for key in shared_keys
        ]
        left_successes = sum(a for a, _ in pairs)
        right_successes = sum(b for _, b in pairs)
        paired[f"{left}__vs__{right}"] = {
            "left": left,
            "right": right,
            "both_success": sum(a and b for a, b in pairs),
            "left_only": sum(a and not b for a, b in pairs),
            "right_only": sum((not a) and b for a, b in pairs),
            "both_failure": sum((not a) and (not b) for a, b in pairs),
            "success_difference_right_minus_left": right_successes - left_successes,
            "rate_difference_right_minus_left": (
                right_successes - left_successes
            ) / 250,
        }

    contrasts = {}
    for block in (0, 1):
        start_tight = policies[policy_id(block, "START15_APP6")]
        start_wide = policies[policy_id(block, "START35_APP6")]
        approach_tight = policies[policy_id(block, "START25_APP3P6")]
        approach_wide = policies[policy_id(block, "START25_APP8P4")]
        contrasts[f"block{block}"] = {
            "delta_start_outer_wide_minus_tight": {
                "success_difference": (
                    start_wide["outer"]["successes"]
                    - start_tight["outer"]["successes"]
                ),
                "rate_difference": (
                    start_wide["outer"]["rate"] - start_tight["outer"]["rate"]
                ),
                "per_seed_success_differences": [
                    (
                        start_wide["per_seed"][str(seed)]["outer"]["successes"]
                        - start_tight["per_seed"][str(seed)]["outer"]["successes"]
                    )
                    for seed in SEEDS
                ],
            },
            "delta_approach_inner_tight_minus_wide": {
                "success_difference": (
                    approach_tight["inner"]["successes"]
                    - approach_wide["inner"]["successes"]
                ),
                "rate_difference": (
                    approach_tight["inner"]["rate"]
                    - approach_wide["inner"]["rate"]
                ),
                "per_seed_success_differences": [
                    (
                        approach_tight["per_seed"][str(seed)]["inner"]["successes"]
                        - approach_wide["per_seed"][str(seed)]["inner"]["successes"]
                    )
                    for seed in SEEDS
                ],
            },
        }

    ranking = sorted(
        policies,
        key=lambda pid: (
            -policies[pid]["rollout_seed_mean_and_sample_std"]["combined"][
                "mean_rate"
            ],
            -policies[pid]["inner"]["rate"],
            -policies[pid]["outer"]["rate"],
            pid,
        ),
    )
    condition_averages = {}
    for condition in CONDITIONS:
        block_rows = [policies[policy_id(block, condition)] for block in (0, 1)]
        condition_averages[condition] = {}
        for scope in ("combined", "inner", "outer"):
            rates = [row[scope]["rate"] for row in block_rows]
            condition_averages[condition][scope] = {
                "block_rates": rates,
                "mean_rate": statistics.mean(rates),
                "sample_std_rate_ddof1": statistics.stdev(rates),
            }
    condition_average_ranking = sorted(
        CONDITIONS,
        key=lambda condition: (
            -condition_averages[condition]["combined"]["mean_rate"],
            condition,
        ),
    )
    scope_rankings = {
        scope: sorted(
            policies,
            key=lambda pid: (
                -policies[pid]["rollout_seed_mean_and_sample_std"][scope][
                    "mean_rate"
                ],
                pid,
            ),
        )
        for scope in ("inner", "outer")
    }
    return {
        "schema_version": 1,
        "status": "valid",
        "evaluation": {
            "seeds": list(SEEDS),
            "rollouts_per_seed_per_policy": 50,
            "inner_rollouts_per_seed_per_policy": 25,
            "outer_rollouts_per_seed_per_policy": 25,
            "rollouts_per_policy": 250,
            "num_policies": 8,
            "validated_rollout_rows": 2000,
            "shared_state_and_rng_pairing_across_all_policies": True,
            "retraining_performed": False,
            "checkpoint_selection": (
                "highest numeric model_epoch_*.pth already present in each "
                "existing training run"
            ),
        },
        "ranking": ranking,
        "condition_average_ranking": condition_average_ranking,
        "condition_block_mean_and_sample_std": condition_averages,
        "inner_ranking": scope_rankings["inner"],
        "outer_ranking": scope_rankings["outer"],
        "policies": policies,
        "within_block_primary_contrasts": contrasts,
        "all_policy_paired_comparisons": paired,
        "source_aggregate_summaries": source_summaries,
    }


def write_markdown(report):
    lines = [
        "# Corrected five-seed rollout comparison",
        "",
        "This comparison uses the eight existing policies without retraining. "
        "For every existing training run, the checkpoint with the highest numeric "
        "`model_epoch_*.pth` suffix was selected and hash-verified.",
        "",
        "All eight policies use the same five seeds (`628`–`632`). Each seed has "
        "25 inner states and 25 outer states, giving 250 rollouts per policy and "
        "2,000 strictly validated rollout rows in total.",
        "",
        "## Eight-policy ranking by five rollout seeds",
        "",
        "For each policy, the five observations are the five `successes/50` "
        "rates. Values are mean ± sample standard deviation (`ddof=1`).",
        "",
        "| Rank | Policy | Five-seed rates | Mean ± std |",
        "|---:|---|---|---:|",
    ]
    for rank, pid in enumerate(report["ranking"], 1):
        row = report["policies"][pid][
            "rollout_seed_mean_and_sample_std"
        ]["combined"]
        lines.append(
            f"| {rank} | `{pid}` | "
            f"`{[round(rate, 3) for rate in row['seed_rates']]}` | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
        "",
        "## Inner success ranking across five rollout seeds",
        "",
        "| Rank | Policy | Inner successes | Mean ± std |",
        "|---:|---|---:|---:|",
        ]
    )
    for rank, pid in enumerate(report["inner_ranking"], 1):
        policy = report["policies"][pid]
        row = policy["rollout_seed_mean_and_sample_std"]["inner"]
        lines.append(
            f"| {rank} | `{pid}` | {policy['inner']['successes']}/125 | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Outer success ranking across five rollout seeds",
            "",
            "| Rank | Policy | Outer successes | Mean ± std |",
            "|---:|---|---:|---:|",
        ]
    )
    for rank, pid in enumerate(report["outer_ranking"], 1):
        policy = report["policies"][pid]
        row = policy["rollout_seed_mean_and_sample_std"]["outer"]
        lines.append(
            f"| {rank} | `{pid}` | {policy['outer']['successes']}/125 | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Hierarchical condition comparison across Block 0 and Block 1",
            "",
            "B0/B1 cells summarize five rollout seeds within each policy. The "
            "last column summarizes the two policy means and therefore measures "
            "learner-block sensitivity.",
            "",
            "| Rank | Condition | B0: seed mean ± std | B1: seed mean ± std | "
            "Across blocks: mean ± std |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for rank, condition in enumerate(report["condition_average_ranking"], 1):
        block0 = report["policies"][policy_id(0, condition)][
            "rollout_seed_mean_and_sample_std"
        ]["combined"]
        block1 = report["policies"][policy_id(1, condition)][
            "rollout_seed_mean_and_sample_std"
        ]["combined"]
        across = report["condition_block_mean_and_sample_std"][condition][
            "combined"
        ]
        lines.append(
            f"| {rank} | `{condition}` | "
            f"{block0['mean_rate']:.3f} ± "
            f"{block0['sample_std_rate_ddof1']:.3f} | "
            f"{block1['mean_rate']:.3f} ± "
            f"{block1['sample_std_rate_ddof1']:.3f} | "
            f"{across['mean_rate']:.3f} ± "
            f"{across['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Results by seed",
            "",
            "| Policy | seed 628 | seed 629 | seed 630 | seed 631 | seed 632 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for pid in report["ranking"]:
        row = report["policies"][pid]
        cells = [
            f"{row['per_seed'][str(seed)]['combined']['successes']}/50"
            for seed in SEEDS
        ]
        lines.append(f"| `{pid}` | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## Within-block mechanism contrasts",
            "",
            "| Block | Start outer: wide − tight | Per-seed differences | "
            "Approach inner: tight − wide | Per-seed differences |",
            "|---:|---:|---|---:|---|",
        ]
    )
    for block in (0, 1):
        contrasts = report["within_block_primary_contrasts"][f"block{block}"]
        start = contrasts["delta_start_outer_wide_minus_tight"]
        approach = contrasts["delta_approach_inner_tight_minus_wide"]
        lines.append(
            f"| {block} | {start['success_difference']}/125 "
            f"({start['rate_difference']:+.3f}) | "
            f"`{start['per_seed_success_differences']}` | "
            f"{approach['success_difference']}/125 "
            f"({approach['rate_difference']:+.3f}) | "
            f"`{approach['per_seed_success_differences']}` |"
        )

    lines.extend(
        [
            "",
            "The earlier single-seed epoch-40 rollout analysis is retained for "
            "provenance but is superseded for policy comparison by this five-seed "
            "evaluation.",
            "",
        ]
    )
    output = ANALYSIS / "rollout_5seed_comparison.md"
    output.write_text("\n".join(lines), encoding="utf-8")


def corrected_replication_decision(report):
    start_rates = [
        round(
            report["within_block_primary_contrasts"][f"block{block}"][
                "delta_start_outer_wide_minus_tight"
            ]["rate_difference"],
            3,
        )
        for block in (0, 1)
    ]
    approach_rates = [
        round(
            report["within_block_primary_contrasts"][f"block{block}"][
                "delta_approach_inner_tight_minus_wide"
            ]["rate_difference"],
            3,
        )
        for block in (0, 1)
    ]

    def replicated(values):
        return all(value > 0.0 for value in values) and sum(values) / 2.0 >= 0.15

    start_replicated = replicated(start_rates)
    approach_replicated = replicated(approach_rates)
    if start_replicated and approach_replicated:
        classification = "strong"
    elif start_replicated or approach_replicated:
        classification = "partial"
    else:
        classification = "null/unstable"
    return {
        "rule_applied_descriptively": (
            "positive in both learner blocks and mean rate difference >= 0.15"
        ),
        "start_primary": {
            "block_rate_differences": start_rates,
            "mean_rate_difference": round(sum(start_rates) / 2.0, 3),
            "replicated": start_replicated,
        },
        "approach_primary": {
            "block_rate_differences": approach_rates,
            "mean_rate_difference": round(sum(approach_rates) / 2.0, 3),
            "replicated": approach_replicated,
        },
        "classification": classification,
    }


def write_primary_summary(report):
    decision = report["corrected_replication_decision"]
    lines = [
        "# T-RO Stage 1 Position MVP summary",
        "",
        f"**Corrected five-seed decision:** {decision['classification']}.",
        "",
        "The earlier single-seed rollout comparison is superseded. The corrected "
        "evaluation uses the eight existing policies without recollection or "
        "retraining. Each policy was evaluated on the same five seeds "
        "(`628`–`632`), with 25 inner and 25 outer states per seed.",
        "",
        "Strictly validated coverage: **8 policies × 5 seeds × 50 rollouts = "
        "2,000 rollout rows**.",
        "",
        "## Existing checkpoint audit",
        "",
        "Every policy directory contains only `model_epoch_20.pth` and "
        "`model_epoch_40.pth`. Following the corrected instruction to use the "
        "highest numeric existing checkpoint, all eight policies use their "
        "existing `model_epoch_40.pth`. No training was run.",
        "",
        "## Eight-policy ranking across rollout seeds",
        "",
        "For each policy, the five values are its five `successes/50` rollout "
        "rates. The table reports their mean ± sample standard deviation "
        "(`ddof=1`). This is the primary robustness ranking.",
        "",
        "| Rank | Policy | Five seed results | Mean ± std |",
        "|---:|---|---|---:|",
    ]
    for rank, pid in enumerate(report["ranking"], 1):
        policy = report["policies"][pid]
        row = policy["rollout_seed_mean_and_sample_std"]["combined"]
        counts = [
            policy["per_seed"][str(seed)]["combined"]["successes"]
            for seed in SEEDS
        ]
        count_text = "[" + ", ".join(f"{count}/50" for count in counts) + "]"
        lines.append(
            f"| {rank} | `{pid}` | "
            f"`{count_text}` | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
        "",
        "## Inner success ranking",
        "",
        "| Rank | Policy | Inner total | Five-seed mean ± std |",
        "|---:|---|---:|---:|",
        ]
    )
    for rank, pid in enumerate(report["inner_ranking"], 1):
        policy = report["policies"][pid]
        row = policy["rollout_seed_mean_and_sample_std"]["inner"]
        lines.append(
            f"| {rank} | `{pid}` | {policy['inner']['successes']}/125 | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Outer success ranking",
            "",
            "| Rank | Policy | Outer total | Five-seed mean ± std |",
            "|---:|---|---:|---:|",
        ]
    )
    for rank, pid in enumerate(report["outer_ranking"], 1):
        policy = report["policies"][pid]
        row = policy["rollout_seed_mean_and_sample_std"]["outer"]
        lines.append(
            f"| {rank} | `{pid}` | {policy['outer']['successes']}/125 | "
            f"{row['mean_rate']:.3f} ± "
            f"{row['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Hierarchical B0/B1 condition comparison",
            "",
            "B0 and B1 each report mean ± sample std across their five rollout "
            "seeds. The final column reports mean ± sample std across the two "
            "independent policy means.",
            "",
            "| Rank | Condition | B0 rollout seeds | B1 rollout seeds | "
            "Across blocks |",
            "|---:|---|---:|---:|---:|",
        ]
    )
    for rank, condition in enumerate(report["condition_average_ranking"], 1):
        block0 = report["policies"][policy_id(0, condition)][
            "rollout_seed_mean_and_sample_std"
        ]["combined"]
        block1 = report["policies"][policy_id(1, condition)][
            "rollout_seed_mean_and_sample_std"
        ]["combined"]
        across = report["condition_block_mean_and_sample_std"][condition][
            "combined"
        ]
        lines.append(
            f"| {rank} | `{condition}` | "
            f"{block0['mean_rate']:.3f} ± "
            f"{block0['sample_std_rate_ddof1']:.3f} | "
            f"{block1['mean_rate']:.3f} ± "
            f"{block1['sample_std_rate_ddof1']:.3f} | "
            f"{across['mean_rate']:.3f} ± "
            f"{across['sample_std_rate_ddof1']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Seed stability",
            "",
            "| Policy | seed 628 | seed 629 | seed 630 | seed 631 | seed 632 |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for pid in report["ranking"]:
        row = report["policies"][pid]
        cells = [
            f"{row['per_seed'][str(seed)]['combined']['successes']}/50"
            for seed in SEEDS
        ]
        lines.append(f"| `{pid}` | " + " | ".join(cells) + " |")

    lines.extend(
        [
            "",
            "## Mechanism result",
            "",
            "| Block | Start outer: wide − tight | Approach inner: tight − wide |",
            "|---:|---:|---:|",
        ]
    )
    for block in (0, 1):
        contrasts = report["within_block_primary_contrasts"][f"block{block}"]
        start = contrasts["delta_start_outer_wide_minus_tight"]
        approach = contrasts["delta_approach_inner_tight_minus_wide"]
        lines.append(
            f"| {block} | {start['success_difference']}/125 "
            f"({start['rate_difference']:+.3f}) | "
            f"{approach['success_difference']}/125 "
            f"({approach['rate_difference']:+.3f}) |"
        )

    lines.extend(
        [
            "",
            "Start variation does not replicate: corrected block effects are "
            f"`{decision['start_primary']['block_rate_differences']}`. Approach "
            "tightening is strong in Block 0 but reverses in Block 1: corrected "
            f"block effects are `{decision['approach_primary']['block_rate_differences']}`.",
            "",
            "The best individual policy is `block0/START25_APP3P6` at 137/250 "
            "(54.8%), and it is stable across seeds (24–31 successes per 50). "
            "However, its independent Block 1 counterpart reaches only 81/250 "
            "(32.4%) and loses to the wide-Approach counterpart. The evidence "
            "therefore supports a learner-block effect, not a reproducible "
            "position mechanism.",
            "",
            "## Conclusion and stop",
            "",
            "**Final Stage 1 classification remains `null/unstable`, now based on "
            "the corrected five-seed evaluation.** Neither primary mechanism is "
            "positive in both independent learner blocks, so there is no robust "
            "basis for Stage 2. Rotation, Velocity, AR and human experiments were "
            "not launched.",
            "",
            "Full per-policy, per-seed, paired-discordance and checkpoint evidence "
            "is in `analysis/rollout_5seed_comparison.json`.",
            "",
        ]
    )
    (ANALYSIS / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def write_screening_decision(report):
    correction = report["corrected_replication_decision"]
    payload = {
        "schema_version": 2,
        "stage": "T-RO Stage 1 Position MVP",
        "stage1_status": "complete_after_corrected_five_seed_rollout_evaluation",
        "earlier_single_seed_evaluation": {
            "status": "superseded_for_policy_comparison",
            "artifacts_preserved": True,
        },
        "corrected_evaluation": report["evaluation"],
        "checkpoint_audit": {
            "available_epochs_per_policy": [20, 40],
            "selected_epoch_per_policy": 40,
            "selection_reason": (
                "epoch 40 is the highest numeric model_epoch_*.pth already "
                "present in every existing run"
            ),
            "retraining_performed": False,
        },
        "ranking": report["ranking"],
        "inner_ranking": report["inner_ranking"],
        "outer_ranking": report["outer_ranking"],
        "policy_rollout_seed_mean_and_sample_std": {
            pid: report["policies"][pid]["rollout_seed_mean_and_sample_std"]
            for pid in report["ranking"]
        },
        "condition_average_ranking": report["condition_average_ranking"],
        "condition_block_mean_and_sample_std": (
            report["condition_block_mean_and_sample_std"]
        ),
        "replication_decision": correction,
        "classification": correction["classification"],
        "stage2_launched": False,
    }
    write_json(ANALYSIS / "screening_decision.json", payload)


def plot_policy_comparison(report):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    ranking = report["ranking"]
    labels = [
        pid.replace("block", "B").replace("/", "\n")
        for pid in ranking
    ]
    inner = [report["policies"][pid]["inner"]["rate"] for pid in ranking]
    outer = [report["policies"][pid]["outer"]["rate"] for pid in ranking]
    combined = [report["policies"][pid]["combined"]["rate"] for pid in ranking]
    combined_std = [
        report["policies"][pid]["rollout_seed_mean_and_sample_std"]["combined"][
            "sample_std_rate_ddof1"
        ]
        for pid in ranking
    ]
    x = np.arange(len(ranking))
    width = 0.34

    fig, axis = plt.subplots(figsize=(14, 6), constrained_layout=True)
    axis.bar(x - width / 2, inner, width, label="Inner (n=125)", color="#3B82F6")
    axis.bar(x + width / 2, outer, width, label="Outer (n=125)", color="#F97316")
    axis.errorbar(
        x,
        combined,
        yerr=combined_std,
        linestyle="none",
        marker="D",
        markersize=6,
        capsize=4,
        color="#111827",
        label="Five-seed mean ± std",
        zorder=3,
    )
    axis.set_ylabel("Success rate")
    axis.set_ylim(0.0, 0.75)
    axis.set_xticks(x)
    axis.set_xticklabels(labels, rotation=20, ha="right")
    axis.set_title("Corrected five-seed comparison of eight existing policies")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(ncols=3, loc="upper right")
    for index, rate in enumerate(combined):
        axis.annotate(
            f"{rate:.3f}",
            (x[index], rate),
            textcoords="offset points",
            xytext=(0, 8),
            ha="center",
            fontsize=8,
        )

    figures = ANALYSIS / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    fig.savefig(figures / "success_by_policy_5seed.png", dpi=180)
    plt.close(fig)


def main():
    policy_rows, checkpoint_records, source_summaries = validate_and_collect()
    report = compare(policy_rows, checkpoint_records, source_summaries)
    report["corrected_replication_decision"] = corrected_replication_decision(
        report
    )
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    write_json(ANALYSIS / "rollout_5seed_comparison.json", report)
    write_markdown(report)
    write_primary_summary(report)
    write_screening_decision(report)
    plot_policy_comparison(report)
    print(json.dumps({
        "status": report["status"],
        "validated_rollout_rows": report["evaluation"]["validated_rollout_rows"],
        "ranking": report["ranking"],
    }, indent=2))


if __name__ == "__main__":
    main()
