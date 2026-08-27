#!/usr/bin/env python3
"""Collect the Target-aligned immutable Control protocol revision.

All physical setup, release, settling and success semantics match the frozen
Target implementation.  The sole teaching-data manipulation retained for
Control is independent sampling from the complete L/R waypoint x-z support on
every attempt, with no personal centre or across-demonstration contraction.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pybullet as pb


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from main_obstacle_transport import (  # noqa: E402
    BOX_INITIAL_Z,
    BOX_START_X_BOUNDS,
    BOX_START_Y_BOUNDS,
    OBSTACLE_XY,
    RELEASE_Z,
    TARGET_XY,
    write_json,
    write_trajectory_plot,
)
from main_obstacle_transport_control_participants import (  # noqa: E402
    CONTROL_PARTICIPANTS,
    NUM_DEMOS_PER_PARTICIPANT,
    WAYPOINT_ROUTE_X_BOUNDS,
    WAYPOINT_Z_BOUNDS,
    sample_broad_waypoint,
    seeded_rng,
    validate_participant_manifest,
    waypoint_spread,
)
from rebuttal_control_pipeline.control_protocol import (  # noqa: E402
    CONTACTS_ARE_DIAGNOSTIC_ONLY,
    ControlObstacleTransportSim,
    GROUP,
    SUCCESS_CRITERION,
    TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE,
    TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
    TARGET_XY_TOLERANCE,
    assert_target_aligned_dependencies,
)


def shared_cube_start(seed, demo_index, attempt_index=0):
    """Target-identical broad start with deterministic retry replenishment."""
    demo_index = int(demo_index)
    attempt_index = int(attempt_index)
    if not 0 <= demo_index < NUM_DEMOS_PER_PARTICIPANT:
        raise ValueError(
            f"demo_index must be in [0, {NUM_DEMOS_PER_PARTICIPANT - 1}]"
        )
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    if attempt_index == 0:
        rng = seeded_rng(seed, 0x53544152)
    else:
        rng = seeded_rng(seed, 0x53544152, attempt_index, 0x5245504C)
    x_bins = rng.permutation(NUM_DEMOS_PER_PARTICIPANT)
    x_jitter = rng.uniform(0.0, 1.0, size=NUM_DEMOS_PER_PARTICIPANT)
    y_values = rng.uniform(*BOX_START_Y_BOUNDS, size=NUM_DEMOS_PER_PARTICIPANT)
    fraction = (
        float(x_bins[demo_index]) + float(x_jitter[demo_index])
    ) / NUM_DEMOS_PER_PARTICIPANT
    x = BOX_START_X_BOUNDS[0] + fraction * (
        BOX_START_X_BOUNDS[1] - BOX_START_X_BOUNDS[0]
    )
    result = {
        "position": [float(x), float(y_values[demo_index]), BOX_INITIAL_Z],
        "source_distribution": {
            "x_bounds": list(BOX_START_X_BOUNDS),
            "y_bounds": list(BOX_START_Y_BOUNDS),
        },
        "sampling": "shared_latin_hypercube_x_with_uniform_y",
        "ee_initial_rule": "[box_x, box_y, box_z + 0.10]",
        "horizontal_ee_offset": [0.0, 0.0],
    }
    if attempt_index > 0:
        result["deterministic_replenishment"] = {
            "attempt_index": attempt_index,
            "rule": (
                "attempt 0 is the authoritative manifest candidate; after a failed "
                "attempt, draw the same demo index from an attempt-seeded 30-point "
                "Latin hypercube over the unchanged broad x/y support"
            ),
            "seed_components": [
                int(seed),
                0x53544152,
                attempt_index,
                0x5245504C,
            ],
            "shared_across_participants": True,
        }
    return result


def participant_task_spec(participant_id, demo_index, attempt_index, seed):
    participant = CONTROL_PARTICIPANTS[participant_id]
    waypoint, waypoint_sampling = sample_broad_waypoint(
        participant_id,
        demo_index,
        attempt_index,
        seed,
    )
    box_sampling = shared_cube_start(seed, demo_index, attempt_index)
    box = box_sampling["position"]
    return {
        "group": GROUP,
        "participant_id": participant_id,
        "condition": participant["route"],
        "demo_index": int(demo_index),
        "attempt_index": int(attempt_index),
        "box_initial_position": box,
        "scripted_ee_initial_position": [box[0], box[1], box[2] + 0.10],
        "participant_waypoint_center": None,
        "middle_waypoint": waypoint.tolist(),
        "waypoint_sampling": waypoint_sampling,
        "transport_z": float(waypoint[2]),
        "release_pose": [TARGET_XY[0], TARGET_XY[1], RELEASE_Z],
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "success_criterion": SUCCESS_CRITERION,
        "success_protocol_scope": GROUP,
        "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
        "shared_cube_start_manifest": f"seed_{seed}_vertical_start_lhs30",
        "box_start_sampling": box_sampling,
        "control_manipulation": {
            "varied_dimension": "position",
            "spatial_consistency_guidance": False,
            "rotation_protocol": "frozen_shared_fixed_orientation",
            "velocity_protocol": "frozen_shared_scripted_timing",
        },
    }


def write_protocol_preview(output_dir, seed):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_waypoints = {
        participant_id: [
            participant_task_spec(participant_id, demo_index, 0, seed)[
                "middle_waypoint"
            ]
            for demo_index in range(NUM_DEMOS_PER_PARTICIPANT)
        ]
        for participant_id in CONTROL_PARTICIPANTS
    }
    manifest = {
        "group": GROUP,
        "seed": int(seed),
        "num_demos_per_participant": NUM_DEMOS_PER_PARTICIPANT,
        "participants": CONTROL_PARTICIPANTS,
        "shared_cube_starts": [
            shared_cube_start(seed, demo_index, 0)
            for demo_index in range(NUM_DEMOS_PER_PARTICIPANT)
        ],
        "physical_success_protocol": {
            "release_ee_z_m": float(RELEASE_Z),
            "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
            "success_criterion": SUCCESS_CRITERION,
            "success_protocol_scope": GROUP,
            "cylinder_tilt_tolerance_degrees": 10.0,
            "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
            "scripted_ee_initial_rule": "[box_x, box_y, box_z + 0.10]",
            "collection_boundary": "after_validated_scripted_grasp_and_lift",
            "first_saved_phase": "policy_inference_start",
            "scripted_setup_saved": False,
            "cube_start_replenishment": (
                "Target-identical deterministic attempt-seeded broad LHS rule"
            ),
        },
        "spatial_protocol": {
            "sampling": "independent_uniform_full_route_xz_rectangle",
            "route_x_bounds": WAYPOINT_ROUTE_X_BOUNDS,
            "waypoint_y": float(OBSTACLE_XY[1]),
            "waypoint_z_bounds": list(WAYPOINT_Z_BOUNDS),
            "personal_waypoint_centers": False,
            "across_demo_contraction": False,
            "invalid_or_unsuccessful_attempts": "reject_and_replenish",
        },
        "paired_rollout_contract": {
            "manifest": str(TARGET_PAIRED_ROLLOUT_MANIFEST_RELATIVE),
            "file_sha256": TARGET_PAIRED_ROLLOUT_MANIFEST_SHA256,
            "reuse_without_regeneration": True,
        },
        "candidate_waypoints": candidate_waypoints,
        "candidate_spread": {
            participant_id: waypoint_spread(points)
            for participant_id, points in candidate_waypoints.items()
        },
    }
    write_json(output_dir / "participant_manifest.json", manifest)

    figure, axes = plt.subplots(
        2,
        5,
        figsize=(16, 7.2),
        sharey=True,
        layout="constrained",
    )
    for axis, (participant_id, participant) in zip(
        axes.flat,
        CONTROL_PARTICIPANTS.items(),
    ):
        waypoints = np.asarray(candidate_waypoints[participant_id])
        demo_numbers = np.arange(1, NUM_DEMOS_PER_PARTICIPANT + 1)
        scatter = axis.scatter(
            waypoints[:, 0],
            waypoints[:, 2],
            c=demo_numbers,
            cmap="viridis",
            s=34,
            edgecolors="none",
        )
        axis.set_title(f"{participant_id} / {participant['route']}")
        axis.set_xlim(WAYPOINT_ROUTE_X_BOUNDS[participant["route"]])
        axis.set_ylim(WAYPOINT_Z_BOUNDS)
        axis.grid(alpha=0.25)
        axis.set_xlabel("waypoint x (m)")
    axes[0, 0].set_ylabel("waypoint z (m)")
    axes[1, 0].set_ylabel("waypoint z (m)")
    figure.colorbar(
        scatter,
        ax=axes.ravel().tolist(),
        label="demonstration index",
        shrink=0.88,
    )
    figure.suptitle(
        "Target-aligned Control: broad independent waypoint sampling"
    )
    figure.savefig(output_dir / "waypoint_spread.png", dpi=170)
    plt.close(figure)
    return manifest


def collect_participant(args, participant_id, demo_indices):
    participant_dir = args.output_dir / participant_id
    participant_dir.mkdir(parents=True, exist_ok=True)
    sim = ControlObstacleTransportSim(
        gui=args.gui,
        output_dir=participant_dir if args.save_raw_frames else None,
        sample_hz=args.sample_hz,
    )
    sim.playback_speed = args.playback_speed
    sim.setup()
    results = []
    try:
        for demo_index in demo_indices:
            for attempt_index in range(args.max_attempts_per_demo):
                spec = participant_task_spec(
                    participant_id,
                    demo_index,
                    attempt_index,
                    args.seed,
                )
                sim.reset_task_state(spec["box_initial_position"])
                video_path = (
                    participant_dir
                    / "videos"
                    / f"demo_{demo_index:02d}_attempt_{attempt_index:02d}.mp4"
                )
                if args.save_videos:
                    sim.start_video(video_path, fps=args.video_fps)
                try:
                    success, details = sim.run_scripted_transport_and_release(
                        spec,
                        save=args.save_raw_frames,
                        demo_index=demo_index,
                    )
                finally:
                    sim.close_video()
                result = {
                    "group": GROUP,
                    "participant_id": participant_id,
                    "condition": spec["condition"],
                    "demo_index": demo_index,
                    "attempt_index": attempt_index,
                    "success": bool(success),
                    "spec": spec,
                    "details": details,
                    "video_path": str(video_path) if args.save_videos else None,
                }
                write_json(
                    participant_dir
                    / "attempts"
                    / f"demo_{demo_index:02d}_attempt_{attempt_index:02d}.json",
                    result,
                )
                write_trajectory_plot(
                    participant_dir
                    / "plots"
                    / f"demo_{demo_index:02d}_attempt_{attempt_index:02d}.png",
                    result,
                    sim._box_trace,
                    sim._ee_trace,
                )
                if success:
                    write_json(participant_dir / f"demo_{demo_index:02d}.json", result)
                    if args.save_raw_frames:
                        sim.write_demo_metadata(
                            {
                                "group": GROUP,
                                "participant_id": participant_id,
                                "condition": spec["condition"],
                                "demo_index": demo_index,
                                "attempt_index": attempt_index,
                                "collection_boundary": (
                                    "after_validated_scripted_grasp_and_lift"
                                ),
                                "first_saved_phase": "policy_inference_start",
                                "scripted_setup_saved": False,
                                "frame_count": sim.frame_index,
                                "spec": spec,
                                "setup_details": details["setup_details"],
                            },
                            merge=False,
                        )
                    results.append(result)
                    print(
                        f"[{participant_id}/{spec['condition']}] "
                        f"demo={demo_index:02d} attempt={attempt_index:02d} "
                        f"success waypoint="
                        f"{np.round(spec['middle_waypoint'], 4).tolist()}",
                        flush=True,
                    )
                    break
                if (
                    args.save_raw_frames
                    and sim.demo_dir is not None
                    and sim.demo_dir.exists()
                ):
                    failed_dir = sim.demo_dir
                    shutil.rmtree(failed_dir)
                    sim.demo_dir = None
                    print(f"Deleted failed raw demo directory: {failed_dir}", flush=True)
            else:
                raise RuntimeError(
                    f"{participant_id} demo {demo_index} failed after "
                    f"{args.max_attempts_per_demo} attempts"
                )
    finally:
        sim.close_video()
        if sim.client is not None:
            pb.disconnect(sim.client)

    summary = {
        "group": GROUP,
        "participant_id": participant_id,
        "participant": CONTROL_PARTICIPANTS[participant_id],
        "seed": args.seed,
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "success_criterion": SUCCESS_CRITERION,
        "success_protocol_scope": GROUP,
        "contacts_are_diagnostic_only": CONTACTS_ARE_DIAGNOSTIC_ONLY,
        "requested_demo_indices": list(demo_indices),
        "successful_demos": len(results),
        "successful_waypoint_spread": waypoint_spread(
            [result["spec"]["middle_waypoint"] for result in results]
        ),
        "successes": results,
    }
    write_json(participant_dir / "summary.json", summary)
    return summary


def merge_participant_summaries(output_dir, participant_ids, demo_indices, seed):
    summaries = []
    for participant_id in participant_ids:
        path = output_dir / participant_id / "summary.json"
        if not path.is_file():
            raise FileNotFoundError(f"Missing participant summary: {path}")
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("group") != GROUP or summary.get("participant_id") != participant_id:
            raise ValueError(f"Participant/group mismatch in {path}")
        if summary.get("requested_demo_indices") != list(demo_indices):
            raise ValueError(f"Demo-index mismatch in {path}")
        if summary.get("successful_demos") != len(demo_indices):
            raise ValueError(f"Incomplete successful demos in {path}")
        summaries.append(summary)
    group_summary = {
        "group": GROUP,
        "seed": int(seed),
        "participant_order": list(participant_ids),
        "demo_indices": list(demo_indices),
        "successful_participants": len(summaries),
        "summaries": summaries,
    }
    write_json(output_dir / "summary.json", group_summary)
    return group_summary


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--participants", nargs="+", default=list(CONTROL_PARTICIPANTS))
    parser.add_argument("--demo-indices", nargs="+", type=int, default=[0])
    parser.add_argument("--all-30", action="store_true")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--max-attempts-per-demo", type=int, default=30)
    parser.add_argument("--sample-hz", type=float, default=8.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--save-videos", action="store_true")
    parser.add_argument("--save-raw-frames", action="store_true")
    parser.add_argument("--video-fps", type=int, default=10)
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--playback-speed", type=float, default=1000.0)
    parser.add_argument("--preview-only", action="store_true")
    parser.add_argument("--skip-preview", action="store_true")
    parser.add_argument("--skip-group-summary", action="store_true")
    parser.add_argument("--merge-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    assert_target_aligned_dependencies(check_paired_manifest=True)
    validate_participant_manifest()
    unknown = sorted(set(args.participants) - set(CONTROL_PARTICIPANTS))
    if unknown:
        raise ValueError(f"Unknown participants: {unknown}")
    demo_indices = (
        list(range(NUM_DEMOS_PER_PARTICIPANT))
        if args.all_30
        else sorted(set(args.demo_indices))
    )
    if (
        not demo_indices
        or min(demo_indices) < 0
        or max(demo_indices) >= NUM_DEMOS_PER_PARTICIPANT
    ):
        raise ValueError("demo indices must be within 0..29")
    if args.seed != 20260806 or args.max_attempts_per_demo != 30:
        raise ValueError("Formal aligned Control protocol requires seed=20260806 and 30 attempts")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not args.skip_preview:
        write_protocol_preview(args.output_dir, args.seed)
    if args.preview_only:
        return
    if args.merge_only:
        group_summary = merge_participant_summaries(
            args.output_dir,
            args.participants,
            demo_indices,
            args.seed,
        )
        print(json.dumps(group_summary, indent=2, sort_keys=True))
        return
    summaries = [
        collect_participant(args, participant_id, demo_indices)
        for participant_id in args.participants
    ]
    group_summary = {
        "group": GROUP,
        "seed": args.seed,
        "participant_order": list(args.participants),
        "demo_indices": demo_indices,
        "successful_participants": len(summaries),
        "summaries": summaries,
    }
    if not args.skip_group_summary:
        write_json(args.output_dir / "summary.json", group_summary)
    print(json.dumps(group_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
