#!/usr/bin/env python3
"""Strictly validate and summarize the five-policy Position confirmation."""

import hashlib
import itertools
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT / "experiments" / "mvp0_position_event" / "confirmation_earlystop"
)
MANIFESTS = EXPERIMENT / "manifests"
ANALYSIS = EXPERIMENT / "analysis"
ROLLOUT_ROOT = ROOT / "dataset" / "tro_position_confirmation" / "rollouts_5seed_n50"
START_MANIFESTS = (
    EXPERIMENT / "manifests" / "rollout_5seed"
)
SEEDS = (628, 629, 630, 631, 632)
BANKS = ("inner", "outer")
CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP6",
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


def validate_and_collect():
    checkpoint_manifest_path = MANIFESTS / "checkpoints.json"
    checkpoint_manifest = read_json(checkpoint_manifest_path)
    if checkpoint_manifest["condition_order"] != list(CONDITIONS):
        raise ValueError("Checkpoint condition order mismatch")
    checkpoint_records = checkpoint_manifest["checkpoints"]
    for condition in CONDITIONS:
        record = checkpoint_records[condition]
        checkpoint = Path(record["path"])
        if sha256(checkpoint) != record["sha256"]:
            raise ValueError(f"{condition}: checkpoint hash mismatch")
        if condition != "START25_APP6":
            available_epochs = [
                int(row["epoch"]) for row in record["available_checkpoints"]
            ]
            if int(record["epoch"]) != max(available_epochs):
                raise ValueError(f"{condition}: selected checkpoint is not latest")

    condition_rows = {condition: {} for condition in CONDITIONS}
    source_summaries = []
    for seed in SEEDS:
        for bank in BANKS:
            bank_id = f"tro_pos_seed{seed}_{bank}_n25_v1"
            start_manifest_path = START_MANIFESTS / f"{bank_id}.json"
            start_manifest = read_json(start_manifest_path)
            if int(start_manifest["seed"]) != seed:
                raise ValueError(f"{bank_id}: seed mismatch")
            if int(start_manifest["num_rollouts"]) != 25:
                raise ValueError(f"{bank_id}: expected 25 states")
            expected_state_ids = [
                row["state_id"] for row in start_manifest["shared_start_records"]
            ]
            if len(expected_state_ids) != 25 or len(set(expected_state_ids)) != 25:
                raise ValueError(f"{bank_id}: state IDs are not unique")

            summary_path = (
                ROLLOUT_ROOT
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
            if aggregate["checkpoint_manifest_sha256"] != sha256(
                checkpoint_manifest_path
            ):
                raise ValueError(f"{summary_path}: checkpoint manifest mismatch")
            if aggregate["start_manifest_sha256"] != sha256(start_manifest_path):
                raise ValueError(f"{summary_path}: start manifest mismatch")

            summaries = {
                row["condition"]: row for row in aggregate["summaries"]
            }
            if tuple(summaries) != CONDITIONS:
                raise ValueError(f"{summary_path}: condition summaries mismatch")
            for condition in CONDITIONS:
                summary = summaries[condition]
                checkpoint = checkpoint_records[condition]
                if summary["checkpoint"] != checkpoint["path"]:
                    raise ValueError(f"{condition}/{seed}/{bank}: checkpoint path")
                if summary["checkpoint_sha256"] != checkpoint["sha256"]:
                    raise ValueError(f"{condition}/{seed}/{bank}: checkpoint hash")
                rows = summary["rollouts"]
                if len(rows) != 25:
                    raise ValueError(f"{condition}/{seed}/{bank}: expected 25 rows")
                if [row["state_id"] for row in rows] != expected_state_ids:
                    raise ValueError(f"{condition}/{seed}/{bank}: state order")
                for row in rows:
                    key = f"seed{seed}/{bank}/{row['state_id']}"
                    if key in condition_rows[condition]:
                        raise ValueError(f"{condition}: duplicate state {key}")
                    if row["bank_id"] != bank_id:
                        raise ValueError(f"{condition}: row bank mismatch")
                    if row["checkpoint_sha256"] != checkpoint["sha256"]:
                        raise ValueError(f"{condition}: row checkpoint mismatch")
                    condition_rows[condition][key] = row

    expected_keys = set(next(iter(condition_rows.values())))
    if len(expected_keys) != 250:
        raise ValueError(f"Expected 250 shared states, got {len(expected_keys)}")
    for condition, rows in condition_rows.items():
        if set(rows) != expected_keys:
            raise ValueError(f"{condition}: states are not exactly paired")
    actual_rows = sum(len(rows) for rows in condition_rows.values())
    if actual_rows != 1250:
        raise ValueError(f"Expected 1,250 rows, got {actual_rows}")
    return condition_rows, checkpoint_records, source_summaries


def difference(policies, left, right, scope):
    return {
        "left": left,
        "right": right,
        "scope": scope,
        "success_difference_right_minus_left": (
            policies[right][scope]["successes"]
            - policies[left][scope]["successes"]
        ),
        "rate_difference_right_minus_left": (
            policies[right][scope]["rate"] - policies[left][scope]["rate"]
        ),
    }


def compare(condition_rows, checkpoint_records, source_summaries):
    policies = {}
    for condition, keyed_rows in condition_rows.items():
        per_seed = {}
        for seed in SEEDS:
            per_seed[str(seed)] = {}
            for bank in BANKS:
                rows = [
                    row
                    for key, row in keyed_rows.items()
                    if key.startswith(f"seed{seed}/{bank}/")
                ]
                per_seed[str(seed)][bank] = stats(rows)
            rows = [
                row
                for key, row in keyed_rows.items()
                if key.startswith(f"seed{seed}/")
            ]
            per_seed[str(seed)]["combined"] = stats(rows)
        all_rows = list(keyed_rows.values())
        policy = {
            "checkpoint": {
                key: checkpoint_records[condition][key]
                for key in ("epoch", "path", "sha256", "selection_rule", "source")
            },
            "combined": stats(all_rows),
            "inner": stats(
                [row for key, row in keyed_rows.items() if "/inner/" in key]
            ),
            "outer": stats(
                [row for key, row in keyed_rows.items() if "/outer/" in key]
            ),
            "per_seed": per_seed,
            "rollout_seed_mean_and_sample_std": {},
        }
        for scope in ("combined", "inner", "outer"):
            rates = [per_seed[str(seed)][scope]["rate"] for seed in SEEDS]
            policy["rollout_seed_mean_and_sample_std"][scope] = {
                "seed_rates": rates,
                "mean_rate": statistics.mean(rates),
                "sample_std_rate_ddof1": statistics.stdev(rates),
            }
        policies[condition] = policy

    rankings = {
        scope: sorted(
            CONDITIONS,
            key=lambda condition: (
                -policies[condition]["rollout_seed_mean_and_sample_std"][scope][
                    "mean_rate"
                ],
                condition,
            ),
        )
        for scope in ("combined", "inner", "outer")
    }
    shared_keys = sorted(next(iter(condition_rows.values())))
    paired = {}
    for left, right in itertools.combinations(CONDITIONS, 2):
        pairs = [
            (
                bool(condition_rows[left][key]["success"]),
                bool(condition_rows[right][key]["success"]),
            )
            for key in shared_keys
        ]
        paired[f"{left}__vs__{right}"] = {
            "both_success": sum(a and b for a, b in pairs),
            f"{left}_only": sum(a and not b for a, b in pairs),
            f"{right}_only": sum((not a) and b for a, b in pairs),
            "both_failure": sum((not a) and (not b) for a, b in pairs),
        }

    contrasts = {
        "start_outer_wide_minus_tight": difference(
            policies, "START15_APP6", "START35_APP6", "outer"
        ),
        "approach_inner_tight_minus_wide": difference(
            policies, "START25_APP8P4", "START25_APP3P6", "inner"
        ),
        "approach_combined_tight_minus_baseline": difference(
            policies, "START25_APP6", "START25_APP3P6", "combined"
        ),
        "approach_inner_tight_minus_baseline": difference(
            policies, "START25_APP6", "START25_APP3P6", "inner"
        ),
        "approach_outer_tight_minus_baseline": difference(
            policies, "START25_APP6", "START25_APP3P6", "outer"
        ),
        "approach_combined_wide_minus_baseline": difference(
            policies, "START25_APP6", "START25_APP8P4", "combined"
        ),
    }
    return {
        "schema_version": 1,
        "status": "valid",
        "evaluation": {
            "seeds": list(SEEDS),
            "conditions": list(CONDITIONS),
            "rollouts_per_seed_per_policy": 50,
            "rollouts_per_policy": 250,
            "validated_rollout_rows": 1250,
            "shared_state_and_rng_pairing_across_all_policies": True,
            "baseline_training_note": (
                "START25_APP6 reuses the accepted legacy S25 epoch-80 policy; "
                "deployment states/RNG are paired, but its demonstration dataset "
                "and training seed differ from the four new policies"
            ),
        },
        "combined_ranking": rankings["combined"],
        "inner_ranking": rankings["inner"],
        "outer_ranking": rankings["outer"],
        "policies": policies,
        "pre_registered_and_baseline_contrasts": contrasts,
        "all_policy_paired_discordances": paired,
        "source_aggregate_summaries": source_summaries,
    }


def write_markdown(report):
    lines = [
        "# T-RO Position early-stopping confirmation",
        "",
        "Strict validation passed for five policies, five shared rollout seeds, "
        "25 inner plus 25 outer states per seed: **1,250 rollout rows**.",
        "",
        "`START25_APP6` is the accepted legacy S25 epoch-80 baseline. Its "
        "deployment states and RNG are exactly paired with the four new policies, "
        "but its demonstration dataset and training seed differ; baseline "
        "differences therefore include training-dataset/seed variation.",
    ]
    for scope, title in (
        ("combined", "Overall"),
        ("inner", "Inner"),
        ("outer", "Outer"),
    ):
        lines.extend(
            [
                "",
                f"## {title} ranking",
                "",
                "| Rank | Condition | Successes | Five-seed mean ± std |",
                "|---:|---|---:|---:|",
            ]
        )
        for rank, condition in enumerate(report[f"{scope}_ranking"], 1):
            policy = report["policies"][condition]
            row = policy["rollout_seed_mean_and_sample_std"][scope]
            lines.append(
                f"| {rank} | `{condition}` | "
                f"{policy[scope]['successes']}/{policy[scope]['total']} | "
                f"{row['mean_rate']:.3f} ± "
                f"{row['sample_std_rate_ddof1']:.3f} |"
            )

    lines.extend(["", "## Contrasts", ""])
    for name, row in report["pre_registered_and_baseline_contrasts"].items():
        lines.append(
            f"- `{name}`: {row['success_difference_right_minus_left']:+d}/"
            f"{report['policies'][row['right']][row['scope']]['total']} "
            f"({row['rate_difference_right_minus_left']:+.3f})."
        )
    output = ANALYSIS / "summary.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    condition_rows, checkpoint_records, source_summaries = validate_and_collect()
    report = compare(condition_rows, checkpoint_records, source_summaries)
    write_json(ANALYSIS / "comparison.json", report)
    write_markdown(report)
    print("Validated 1,250/1,250 rollout rows")
    print(f"Wrote {ANALYSIS / 'comparison.json'}")
    print(f"Wrote {ANALYSIS / 'summary.md'}")


if __name__ == "__main__":
    main()
