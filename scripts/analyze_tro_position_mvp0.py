#!/usr/bin/env python3
"""Strict rollout validation and pre-registered Stage 1 analysis."""

import argparse
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "mvp0_position_event"
MANIFESTS = EXPERIMENT / "manifests"
ANALYSIS = EXPERIMENT / "analysis"
DATA_ROOT = ROOT / "dataset" / "tro_position_mvp0"
CONDITIONS = (
    "START15_APP6",
    "START35_APP6",
    "START25_APP3P6",
    "START25_APP8P4",
)
BANK_REFERENCE = "legacy_seed628_reference_r00_r25_n25_v1"
BANK_OUTER = "legacy_seed628_outer_r25_r35_n25_v1"
BANKS = (BANK_REFERENCE, BANK_OUTER)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def wilson(successes, total, z=1.959963984540054):
    p = successes / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = z * math.sqrt(
        p * (1.0 - p) / total + z * z / (4.0 * total * total)
    ) / denominator
    return [center - margin, center + margin]


def paired(rows_left, rows_right, left, right):
    left_by_state = {row["state_id"]: bool(row["success"]) for row in rows_left}
    right_by_state = {row["state_id"]: bool(row["success"]) for row in rows_right}
    if set(left_by_state) != set(right_by_state):
        raise ValueError(f"Paired state IDs differ for {left} vs {right}")
    pairs = [(left_by_state[state], right_by_state[state]) for state in left_by_state]
    return {
        "both_success": sum(a and b for a, b in pairs),
        f"{left}_only": sum(a and not b for a, b in pairs),
        f"{right}_only": sum((not a) and b for a, b in pairs),
        "both_failure": sum((not a) and (not b) for a, b in pairs),
    }


def validate_block(block):
    checkpoint_manifest = read_json(MANIFESTS / f"checkpoints_b{block}.json")
    if tuple(checkpoint_manifest["condition_order"]) != CONDITIONS:
        raise ValueError("Checkpoint condition order differs from the frozen order")
    rows_by_bank_condition = {}
    all_rows = []
    statistics = {}
    discordances = {}
    for bank in BANKS:
        child = read_json(MANIFESTS / f"{bank}.json")
        expected_states = child["state_ids"]
        output_root = DATA_ROOT / f"block{block}" / "rollouts" / bank
        aggregate = read_json(output_root / "summary_seed628_n25.json")
        if tuple(aggregate["condition_order"]) != CONDITIONS:
            raise ValueError(f"{bank}: aggregate condition order mismatch")
        if aggregate.get("bank_id") != bank:
            raise ValueError(f"{bank}: aggregate bank_id mismatch")
        summaries = {row["condition"]: row for row in aggregate["summaries"]}
        if tuple(summaries) != CONDITIONS:
            raise ValueError(f"{bank}: missing or reordered condition summaries")
        for condition in CONDITIONS:
            summary = summaries[condition]
            expected_checkpoint = checkpoint_manifest["checkpoints"][condition]
            if summary["checkpoint_sha256"] != expected_checkpoint["sha256"]:
                raise ValueError(f"{bank}/{condition}: checkpoint hash mismatch")
            if int(summary.get("block", -1)) != block:
                raise ValueError(f"{bank}/{condition}: block mismatch")
            if summary.get("bank_id") != bank:
                raise ValueError(f"{bank}/{condition}: bank mismatch")
            rows = summary["rollouts"]
            if len(rows) != 25:
                raise ValueError(f"{bank}/{condition}: expected 25 rows, got {len(rows)}")
            if [row["state_id"] for row in rows] != expected_states:
                raise ValueError(f"{bank}/{condition}: state coverage/order mismatch")
            for local_index, row in enumerate(rows):
                required = {
                    "condition",
                    "block",
                    "bank_id",
                    "state_id",
                    "checkpoint_sha256",
                    "success",
                    "final_cube_z",
                    "steps",
                }
                if not required <= set(row):
                    raise ValueError(
                        f"{bank}/{condition}/{local_index}: missing {sorted(required - set(row))}"
                    )
                if row["condition"] != condition or int(row["block"]) != block:
                    raise ValueError(f"{bank}/{condition}/{local_index}: identity mismatch")
                if row["bank_id"] != bank:
                    raise ValueError(f"{bank}/{condition}/{local_index}: bank mismatch")
                if row["checkpoint_sha256"] != expected_checkpoint["sha256"]:
                    raise ValueError(f"{bank}/{condition}/{local_index}: checkpoint mismatch")
            rows_by_bank_condition[(bank, condition)] = rows
            successes = sum(bool(row["success"]) for row in rows)
            statistics.setdefault(condition, {})[bank] = {
                "successes": successes,
                "total": 25,
                "rate": successes / 25,
                "wilson_95": wilson(successes, 25),
            }
            all_rows.extend(rows)
        discordances[bank] = {
            "start": paired(
                rows_by_bank_condition[(bank, "START15_APP6")],
                rows_by_bank_condition[(bank, "START35_APP6")],
                "START15_APP6",
                "START35_APP6",
            ),
            "approach": paired(
                rows_by_bank_condition[(bank, "START25_APP3P6")],
                rows_by_bank_condition[(bank, "START25_APP8P4")],
                "START25_APP3P6",
                "START25_APP8P4",
            ),
        }
    if len(all_rows) != 200:
        raise ValueError(f"Block {block}: expected exactly 200 rollout rows, got {len(all_rows)}")

    counts = {
        condition: {
            "reference": statistics[condition][BANK_REFERENCE]["successes"],
            "outer": statistics[condition][BANK_OUTER]["successes"],
        }
        for condition in CONDITIONS
    }
    contrasts = {
        "delta_start_outer": {
            "success_difference": counts["START35_APP6"]["outer"]
            - counts["START15_APP6"]["outer"],
        },
        "delta_start_reference": {
            "success_difference": counts["START35_APP6"]["reference"]
            - counts["START15_APP6"]["reference"],
        },
        "delta_approach_reference": {
            "success_difference": counts["START25_APP3P6"]["reference"]
            - counts["START25_APP8P4"]["reference"],
        },
        "delta_approach_outer": {
            "success_difference": counts["START25_APP3P6"]["outer"]
            - counts["START25_APP8P4"]["outer"],
        },
    }
    for record in contrasts.values():
        record["rate_difference"] = record["success_difference"] / 25
    if block == 0:
        continuation = {
            "threshold_success_difference": 4,
            "threshold_rate_difference": 0.16,
            "delta_start_outer_pass": contrasts["delta_start_outer"]["success_difference"] >= 4,
            "delta_approach_reference_pass": (
                contrasts["delta_approach_reference"]["success_difference"] >= 4
            ),
        }
        continuation["continue_block1"] = (
            continuation["delta_start_outer_pass"]
            or continuation["delta_approach_reference_pass"]
        )
    else:
        continuation = None
    report = {
        "schema_version": 1,
        "block": block,
        "status": "valid",
        "validated_rollout_rows": len(all_rows),
        "condition_order": list(CONDITIONS),
        "banks": list(BANKS),
        "statistics": statistics,
        "success_counts": counts,
        "contrasts": contrasts,
        "paired_success_discordances": discordances,
        "continuation_rule": continuation,
    }
    output = ANALYSIS / ("block0_screening.json" if block == 0 else "block1_screening.json")
    write_json(output, report)
    if block == 0:
        decision = {
            "schema_version": 1,
            "stage": "T-RO Stage 1 Position MVP",
            "block0_valid": True,
            "pre_registered_rule": (
                "delta_start_outer >= 4/25 OR "
                "delta_approach_reference >= 4/25"
            ),
            **continuation,
            "block1_status": (
                "required_not_yet_run"
                if continuation["continue_block1"]
                else "skipped_for_pre_registered_futility"
            ),
            "stage1_status": (
                "awaiting_independent_block1"
                if continuation["continue_block1"]
                else "complete_futility_null"
            ),
        }
        write_json(ANALYSIS / "screening_decision.json", decision)
    print(json.dumps(report, indent=2))
    return report


def plot_figures(blocks):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figures = ANALYSIS / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    colors = ["#3B82F6", "#F97316", "#10B981", "#A855F7"]

    fig, axes = plt.subplots(2, 4, figsize=(15, 7), constrained_layout=True)
    for col, condition in enumerate(CONDITIONS):
        metadata = []
        for block in blocks:
            raw = DATA_ROOT / f"block{block}" / "raw" / condition
            metadata.extend(
                read_json(path)
                for path in sorted(
                    raw.glob("demo_*/metadata.json"),
                    key=lambda p: int(p.parent.name.split("_", 1)[1]),
                )
            )
        starts = [row["corridor_start_delta"] for row in metadata]
        approaches = [row["pre_grasp_delta"] for row in metadata]
        axes[0, col].scatter(
            [row[0] for row in starts],
            [row[2] for row in starts],
            s=18,
            alpha=0.75,
            color=colors[col],
        )
        axes[1, col].scatter(
            [row[0] for row in approaches],
            [row[1] for row in approaches],
            s=18,
            alpha=0.75,
            color=colors[col],
        )
        axes[0, col].set_title(condition)
        axes[0, col].set_aspect("equal")
        axes[1, col].set_aspect("equal")
        axes[0, col].set_xlabel("Start dx (m)")
        axes[0, col].set_ylabel("Start dz (m)")
        axes[1, col].set_xlabel("Approach dx (m)")
        axes[1, col].set_ylabel("Approach dy (m)")
    fig.savefig(figures / "sampled_start_approach_offsets.png", dpi=180)
    plt.close(fig)

    reports = [read_json(ANALYSIS / f"block{block}_screening.json") for block in blocks]
    fig, axes = plt.subplots(1, len(blocks), figsize=(8 * len(blocks), 5), squeeze=False)
    x = list(range(len(CONDITIONS)))
    width = 0.36
    for ax, block, report in zip(axes[0], blocks, reports):
        reference = [report["success_counts"][c]["reference"] for c in CONDITIONS]
        outer = [report["success_counts"][c]["outer"] for c in CONDITIONS]
        ax.bar([v - width / 2 for v in x], reference, width, label="Reference bank")
        ax.bar([v + width / 2 for v in x], outer, width, label="Outer bank")
        ax.set_xticks(x, CONDITIONS, rotation=20, ha="right")
        ax.set_ylim(0, 25)
        ax.set_ylabel("Successes / 25")
        ax.set_title(f"Block {block}")
        ax.legend()
    fig.tight_layout()
    fig.savefig(figures / "success_by_bank.png", dpi=180)
    plt.close(fig)


def final_report(_args):
    block0 = read_json(ANALYSIS / "block0_screening.json")
    continue_block1 = block0["continuation_rule"]["continue_block1"]
    blocks = [0]
    block1 = None
    if continue_block1:
        block1 = read_json(ANALYSIS / "block1_screening.json")
        if block1["validated_rollout_rows"] != 200:
            raise ValueError("Block 1 is required but incomplete")
        blocks.append(1)

    def contrast_values(name):
        values = [block0["contrasts"][name]["rate_difference"]]
        if block1 is not None:
            values.append(block1["contrasts"][name]["rate_difference"])
        return values

    def replicated(name):
        if block1 is None:
            return False
        values = contrast_values(name)
        return all(value > 0 for value in values) and sum(values) / 2 >= 0.15

    start_replicated = replicated("delta_start_outer")
    approach_replicated = replicated("delta_approach_reference")
    if not continue_block1:
        classification = "null/futility"
        stage_status = "complete_futility_null"
    elif start_replicated and approach_replicated:
        classification = "strong"
        stage_status = "complete"
    elif start_replicated or approach_replicated:
        classification = "partial"
        stage_status = "complete"
    else:
        classification = "null/unstable"
        stage_status = "complete"

    decision = {
        "schema_version": 1,
        "stage": "T-RO Stage 1 Position MVP",
        "pre_registered_rule": (
            "delta_start_outer >= 4/25 OR delta_approach_reference >= 4/25"
        ),
        "block0": block0["continuation_rule"],
        "block1_executed": continue_block1,
        "block1_status": "complete" if continue_block1 else "skipped_for_pre_registered_futility",
        "replication_rule": (
            "positive in both blocks and mean rate difference across blocks >= 0.15"
        ),
        "start_primary_replicated": start_replicated,
        "approach_primary_replicated": approach_replicated,
        "primary_contrasts": {
            "delta_start_outer": {
                "block_rate_differences": contrast_values("delta_start_outer"),
                "mean_rate_difference": round((
                    sum(contrast_values("delta_start_outer"))
                    / len(contrast_values("delta_start_outer"))
                ), 12),
                "replicated": start_replicated,
            },
            "delta_approach_reference": {
                "block_rate_differences": contrast_values(
                    "delta_approach_reference"
                ),
                "mean_rate_difference": round((
                    sum(contrast_values("delta_approach_reference"))
                    / len(contrast_values("delta_approach_reference"))
                ), 12),
                "replicated": approach_replicated,
            },
        },
        "classification": classification,
        "stage1_status": stage_status,
        "stage2_launched": False,
    }
    write_json(ANALYSIS / "screening_decision.json", decision)

    reports = [block0] + ([block1] if block1 else [])
    lines = [
        "# T-RO Stage 1 Position MVP summary",
        "",
        f"**Decision:** {classification}.",
        "",
        "The accepted `Start → Approach → Descent → Grasp → Lift` trajectory, "
        "fixed grasp/lift targets, 30-demonstration budget, legacy learner, "
        "40-epoch checkpoint rule and two reused legacy state banks were held fixed.",
        "",
        "## New Stage 1 results",
        "",
    ]
    for report in reports:
        block = report["block"]
        lines.extend(
            [
                f"### Block {block}",
                "",
                "| Condition | Reference bank | Wilson 95% | Outer bank | Wilson 95% |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for condition in CONDITIONS:
            ref = report["statistics"][condition][BANK_REFERENCE]
            outer = report["statistics"][condition][BANK_OUTER]
            lines.append(
                f"| `{condition}` | {ref['successes']}/25 | "
                f"[{ref['wilson_95'][0]:.3f}, {ref['wilson_95'][1]:.3f}] | "
                f"{outer['successes']}/25 | "
                f"[{outer['wilson_95'][0]:.3f}, {outer['wilson_95'][1]:.3f}] |"
            )
        lines.extend(["", "| Contrast | Difference | Rate difference |", "|---|---:|---:|"])
        for name, record in report["contrasts"].items():
            lines.append(
                f"| `{name}` | {record['success_difference']}/25 | "
                f"{record['rate_difference']:.3f} |"
            )
        lines.extend(
            [
                "",
                "| Bank | Paired contrast | Both success | Left only | "
                "Right only | Both failure |",
                "|---|---|---:|---:|---:|---:|",
            ]
        )
        paired_specs = (
            (
                "Start",
                "start",
                "START15_APP6",
                "START35_APP6",
            ),
            (
                "Approach",
                "approach",
                "START25_APP3P6",
                "START25_APP8P4",
            ),
        )
        for bank, bank_label in (
            (BANK_REFERENCE, "Reference"),
            (BANK_OUTER, "Outer"),
        ):
            for label, key, left, right in paired_specs:
                record = report["paired_success_discordances"][bank][key]
                lines.append(
                    f"| {bank_label} | {label} | {record['both_success']} | "
                    f"{record[f'{left}_only']} | {record[f'{right}_only']} | "
                    f"{record['both_failure']} |"
                )
        lines.append("")
    lines.extend(
        [
            "## Sequential decision",
            "",
            "Block 1 was "
            + ("executed because at least one primary Block 0 contrast reached 4/25."
               if continue_block1
               else "skipped because neither primary Block 0 contrast reached 4/25."),
            "",
            (
                "Start primary replication: "
                f"{contrast_values('delta_start_outer')} with mean "
                f"{sum(contrast_values('delta_start_outer')) / len(contrast_values('delta_start_outer')):.3f}; "
                f"replicated = {str(start_replicated).lower()}."
            ),
            "",
            (
                "Approach primary replication: "
                f"{contrast_values('delta_approach_reference')} with mean "
                f"{sum(contrast_values('delta_approach_reference')) / len(contrast_values('delta_approach_reference')):.3f}; "
                f"replicated = {str(approach_replicated).lower()}."
            ),
            "",
            "This is sequential engineering screening, not a formal significance test.",
            "",
            "## Historical context only",
            "",
            "| Legacy coupled condition | Reference bank | Outer bank |",
            "|---|---:|---:|",
            "| S15 `(15 cm, 3.6 cm)` | 14/25 | 4/25 |",
            "| S25 `(25 cm, 6.0 cm)` | 8/25 | 10/25 |",
            "| S35 `(35 cm, 8.4 cm)` | 5/25 | 2/25 |",
            "",
            "S15 and S35 changed both radii and are not relabelled as new "
            "single-stage conditions. S25 used an epoch-80 checkpoint and remains "
            "a historical reference only.",
            "",
            "## Limits and stop",
            "",
            "The dataset-policy block is the independent learner replicate; paired "
            "rollouts are deployment trials. Results apply to this fixed learner, "
            "30-demonstration budget and tested grasping task. Stage 2, Rotation, "
            "Velocity, AR and human experiments were not launched.",
        ]
    )
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot_figures(blocks)
    print(json.dumps(decision, indent=2))


def parse_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    block = subparsers.add_parser("validate-block")
    block.add_argument("--block", type=int, choices=(0, 1), required=True)
    block.set_defaults(func=lambda args: validate_block(args.block))
    final = subparsers.add_parser("final")
    final.set_defaults(func=final_report)
    return parser.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
