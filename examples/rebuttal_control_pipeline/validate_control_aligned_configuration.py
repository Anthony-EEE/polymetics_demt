#!/usr/bin/env python3
"""Validate the frozen Control configuration before collection is authorised."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXAMPLES_DIR.parent
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_control_pipeline.collect_control_aligned import (  # noqa: E402
    participant_task_spec,
    shared_cube_start,
)
from rebuttal_control_pipeline.control_protocol import (  # noqa: E402
    CONTACTS_ARE_DIAGNOSTIC_ONLY,
    CYLINDER_TILT_TOLERANCE_DEGREES,
    EXPECTED_RELEASE_Z,
    FORMAL_SEED,
    GROUP,
    REVISION_ROOT_RELATIVE,
    SUCCESS_CRITERION,
    TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
    TARGET_XY_TOLERANCE,
    assert_target_aligned_dependencies,
    sha256,
)


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT / REVISION_ROOT_RELATIVE,
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    expected_root = (REPO_ROOT / REVISION_ROOT_RELATIVE).resolve()
    if root != expected_root:
        raise ValueError(f"Configuration validator is frozen to {expected_root}")
    output = (
        args.output or root / "configuration_validation_report.json"
    ).resolve()
    if output.exists():
        raise FileExistsError(output)

    errors = []
    assert_target_aligned_dependencies(check_paired_manifest=True)
    configuration = load_json(root / "protocol_configuration.json")
    manifest = load_json(root / "participant_manifest.json")
    preflight = load_json(root / "diagnostics/ik_candidate_preflight.json")

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(configuration.get("group") == GROUP, "wrong_configuration_group")
    require(configuration.get("seed") == FORMAL_SEED, "wrong_configuration_seed")
    require(
        configuration.get("status")
        == "CONFIGURATION_PREPARED_AWAITING_EXPLICIT_START",
        "wrong_configuration_status",
    )
    require(configuration.get("collection_started") is False, "collection_marked_started")
    require(
        configuration.get("collection_start_gate")
        == "wait for explicit user instruction: 开始收集数据",
        "wrong_collection_start_gate",
    )
    alignment = configuration.get("target_alignment", {})
    for key, expected in {
        "release_ee_z_m": EXPECTED_RELEASE_Z,
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "cylinder_tilt_tolerance_degrees": CYLINDER_TILT_TOLERANCE_DEGREES,
        "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
        "success_criterion": SUCCESS_CRITERION,
        "dual_offset_or_cartesian_diagnostic_revision_applied": False,
    }.items():
        require(alignment.get(key) == expected, f"alignment_mismatch:{key}")
    require(
        configuration.get("paired_rollout_contract", {}).get("file_sha256")
        == TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
        "wrong_paired_rollout_hash",
    )
    require(
        configuration.get("paired_rollout_contract", {}).get(
            "reuse_without_regeneration"
        )
        is True,
        "paired_rollout_regeneration_not_forbidden",
    )

    for name, record in configuration.get(
        "software_and_dependency_hashes", {}
    ).items():
        path = Path(record.get("path", ""))
        require(path.is_file(), f"missing_frozen_dependency:{name}:{path}")
        if path.is_file():
            require(
                sha256(path) == record.get("sha256"),
                f"frozen_dependency_hash_changed:{name}",
            )

    require(manifest.get("group") == GROUP, "wrong_manifest_group")
    require(manifest.get("seed") == FORMAL_SEED, "wrong_manifest_seed")
    require(manifest.get("num_demos_per_participant") == 30, "wrong_demo_budget")
    require(len(manifest.get("participants", {})) == 10, "wrong_participant_count")
    require(len(manifest.get("shared_cube_starts", [])) == 30, "wrong_start_count")
    for demo_index in range(30):
        require(
            manifest["shared_cube_starts"][demo_index]
            == shared_cube_start(FORMAL_SEED, demo_index, 0),
            f"attempt0_start_mismatch:{demo_index}",
        )
    for participant_id in manifest.get("participants", {}):
        for demo_index in range(30):
            spec = participant_task_spec(
                participant_id,
                demo_index,
                0,
                FORMAL_SEED,
            )
            box = spec["box_initial_position"]
            require(
                spec["scripted_ee_initial_position"]
                == [box[0], box[1], box[2] + 0.10],
                f"initial_ee_mismatch:{participant_id}:{demo_index}",
            )
            require(
                spec["release_pose"] == [0.5, 0.5, EXPECTED_RELEASE_Z],
                f"release_pose_mismatch:{participant_id}:{demo_index}",
            )

    require(preflight.get("group") == GROUP, "wrong_preflight_group")
    require(preflight.get("policy_blind") is True, "preflight_not_policy_blind")
    require(
        preflight.get("check_scope")
        == "IK feasibility only; no collection outcome or learned policy queried",
        "wrong_preflight_scope",
    )
    require(preflight.get("accepted_count") == 300, "preflight_not_300")
    require(preflight.get("all_300_have_feasible_candidate") is True, "preflight_failed")
    require(
        max(row["attempt_index"] for row in preflight.get("accepted", [])) <= 29,
        "preflight_exceeds_attempt_cap",
    )

    formal_dirs = sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith("C") and path.name[1:].isdigit()
    )
    require(not formal_dirs, f"formal_collection_dirs_exist:{formal_dirs}")
    require(not (root / "summary.json").exists(), "formal_group_summary_exists")
    require(not (root / "validation_report.json").exists(), "formal_validation_report_exists")

    report = {
        "schema_version": 1,
        "group": GROUP,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "passed": not errors,
        "errors": errors,
        "collection_started": False,
        "formal_participant_directories": formal_dirs,
        "preflight": {
            "accepted": preflight.get("accepted_count"),
            "rejected": preflight.get("rejected_count"),
            "max_first_feasible_attempt": max(
                row["attempt_index"] for row in preflight.get("accepted", [])
            ),
            "sha256": sha256(root / "diagnostics/ik_candidate_preflight.json"),
        },
        "hashes": {
            "protocol_configuration": sha256(root / "protocol_configuration.json"),
            "participant_manifest": sha256(root / "participant_manifest.json"),
            "paired_rollout_manifest": TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
            "configuration_validator": sha256(Path(__file__).resolve()),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
