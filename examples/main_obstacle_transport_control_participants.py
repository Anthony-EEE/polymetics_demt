#!/usr/bin/env python3
"""Synthetic control-participant obstacle-transport demonstrations.

Control participants receive no spatial-consistency guidance.  Every retained
demonstration independently samples a middle waypoint from the full route
support.  Invalid or unsuccessful samples are rejected and replenished until
each participant has exactly 30 successful demonstrations.

The frozen simulator, cube starts, orientation, timing, collection boundary,
and success rule are identical to the target group.  Only the waypoint
distribution differs: there is no personal centre and no across-demo
contraction.
"""

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
import pybullet as pb

from main_obstacle_transport import (
    BOX_INITIAL_Z,
    BOX_START_X_BOUNDS,
    BOX_START_Y_BOUNDS,
    OBSTACLE_XY,
    ObstacleTransportSim,
    TARGET_XY,
    write_json,
    write_trajectory_plot,
)


EXPERIMENT_GROUP = "simulation_control_group"
NUM_DEMOS_PER_PARTICIPANT = 30
WAYPOINT_ROUTE_X_BOUNDS = {"L": (0.10, 0.30), "R": (0.70, 0.90)}
WAYPOINT_Z_BOUNDS = (0.19, 0.29)

CONTROL_PARTICIPANTS = {
    **{f"C{index:02d}": {"route": "L"} for index in range(1, 6)},
    **{f"C{index:02d}": {"route": "R"} for index in range(6, 11)},
}


def seeded_rng(*components):
    return np.random.default_rng(
        np.random.SeedSequence([int(value) for value in components])
    )


def shared_cube_start(seed, demo_index):
    """Match the Target group's frozen broad cube-start manifest exactly."""
    if not 0 <= int(demo_index) < NUM_DEMOS_PER_PARTICIPANT:
        raise ValueError(
            f"demo_index must be in [0, {NUM_DEMOS_PER_PARTICIPANT - 1}]"
        )
    rng = seeded_rng(seed, 0x53544152)
    x_bins = rng.permutation(NUM_DEMOS_PER_PARTICIPANT)
    x_jitter = rng.uniform(0.0, 1.0, size=NUM_DEMOS_PER_PARTICIPANT)
    y_values = rng.uniform(*BOX_START_Y_BOUNDS, size=NUM_DEMOS_PER_PARTICIPANT)
    fraction = (
        float(x_bins[demo_index]) + float(x_jitter[demo_index])
    ) / NUM_DEMOS_PER_PARTICIPANT
    x = BOX_START_X_BOUNDS[0] + fraction * (
        BOX_START_X_BOUNDS[1] - BOX_START_X_BOUNDS[0]
    )
    position = [float(x), float(y_values[demo_index]), BOX_INITIAL_Z]
    return {
        "position": position,
        "source_distribution": {
            "x_bounds": list(BOX_START_X_BOUNDS),
            "y_bounds": list(BOX_START_Y_BOUNDS),
        },
        "sampling": "shared_latin_hypercube_x_with_uniform_y",
        "ee_initial_rule": "[box_x, box_y, box_z + 0.10]",
        "horizontal_ee_offset": [0.0, 0.0],
    }


def sample_broad_waypoint(participant_id, demo_index, attempt_index, seed):
    """Independently sample the full route rectangle for every attempt."""
    participant = CONTROL_PARTICIPANTS[participant_id]
    route = participant["route"]
    participant_number = int(participant_id[1:])
    rng = seeded_rng(
        seed,
        participant_number,
        demo_index,
        attempt_index,
        0x4354524C,
    )
    x_bounds = WAYPOINT_ROUTE_X_BOUNDS[route]
    x = float(rng.uniform(*x_bounds))
    z = float(rng.uniform(*WAYPOINT_Z_BOUNDS))
    waypoint = np.asarray([x, OBSTACLE_XY[1], z], dtype=float)
    return waypoint, {
        "sampling": "independent_uniform_full_route_xz_rectangle",
        "position_consistency_guidance": False,
        "personal_waypoint_center": None,
        "across_demo_contraction": False,
        "x_bounds": list(x_bounds),
        "y_fixed": float(OBSTACLE_XY[1]),
        "z_bounds": list(WAYPOINT_Z_BOUNDS),
        "x_draw": x,
        "z_draw": z,
    }


def participant_task_spec(participant_id, demo_index, attempt_index, seed):
    participant = CONTROL_PARTICIPANTS[participant_id]
    waypoint, waypoint_sampling = sample_broad_waypoint(
        participant_id,
        demo_index,
        attempt_index,
        seed,
    )
    box_sampling = shared_cube_start(seed, demo_index)
    box = box_sampling["position"]
    return {
        "group": EXPERIMENT_GROUP,
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
        "release_pose": [TARGET_XY[0], TARGET_XY[1], float(waypoint[2])],
        "shared_cube_start_manifest": f"seed_{seed}_vertical_start_lhs30",
        "box_start_sampling": box_sampling,
        "control_manipulation": {
            "varied_dimension": "position",
            "spatial_consistency_guidance": False,
            "rotation_protocol": "frozen_shared_fixed_orientation",
            "velocity_protocol": "frozen_shared_scripted_timing",
        },
    }


def validate_participant_manifest():
    participant_ids = list(CONTROL_PARTICIPANTS)
    expected = [f"C{index:02d}" for index in range(1, 11)]
    if participant_ids != expected:
        raise ValueError(f"Unexpected Control participant order: {participant_ids}")
    left = [row for row in CONTROL_PARTICIPANTS.values() if row["route"] == "L"]
    right = [row for row in CONTROL_PARTICIPANTS.values() if row["route"] == "R"]
    if len(left) != 5 or len(right) != 5:
        raise ValueError("Expected exactly five L and five R Control participants")
    if WAYPOINT_ROUTE_X_BOUNDS["L"][1] >= OBSTACLE_XY[0]:
        raise ValueError("L route support crosses the obstacle centre line")
    if WAYPOINT_ROUTE_X_BOUNDS["R"][0] <= OBSTACLE_XY[0]:
        raise ValueError("R route support crosses the obstacle centre line")


def waypoint_spread(waypoints):
    points = np.asarray(waypoints, dtype=float)
    sample_ddof = 1 if points.shape[0] > 1 else 0
    return {
        "count": int(points.shape[0]),
        "unique_count": int(np.unique(np.round(points[:, [0, 2]], 12), axis=0).shape[0]),
        "x_min": float(points[:, 0].min()),
        "x_max": float(points[:, 0].max()),
        "x_span": float(np.ptp(points[:, 0])),
        "x_std": float(np.std(points[:, 0], ddof=sample_ddof)),
        "z_min": float(points[:, 2].min()),
        "z_max": float(points[:, 2].max()),
        "z_span": float(np.ptp(points[:, 2])),
        "z_std": float(np.std(points[:, 2], ddof=sample_ddof)),
    }


def write_protocol_preview(output_dir, seed):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
        "group": EXPERIMENT_GROUP,
        "seed": int(seed),
        "num_demos_per_participant": NUM_DEMOS_PER_PARTICIPANT,
        "participants": CONTROL_PARTICIPANTS,
        "shared_cube_starts": [
            shared_cube_start(seed, demo_index)
            for demo_index in range(NUM_DEMOS_PER_PARTICIPANT)
        ],
        "spatial_protocol": {
            "sampling": "independent_uniform_full_route_xz_rectangle",
            "route_x_bounds": WAYPOINT_ROUTE_X_BOUNDS,
            "waypoint_y": float(OBSTACLE_XY[1]),
            "waypoint_z_bounds": list(WAYPOINT_Z_BOUNDS),
            "personal_waypoint_centers": False,
            "across_demo_contraction": False,
            "invalid_or_unsuccessful_attempts": "reject_and_replenish",
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
        x_bounds = WAYPOINT_ROUTE_X_BOUNDS[participant["route"]]
        axis.set_title(f"{participant_id} / {participant['route']}")
        axis.set_xlim(x_bounds)
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
        "Synthetic control participants: broad independent waypoint sampling"
    )
    figure.savefig(output_dir / "waypoint_spread.png", dpi=170)
    plt.close(figure)
    return manifest


def collect_participant(args, participant_id, demo_indices):
    participant_dir = args.output_dir / participant_id
    participant_dir.mkdir(parents=True, exist_ok=True)
    sim = ObstacleTransportSim(
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
                    "group": EXPERIMENT_GROUP,
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
                                "group": EXPERIMENT_GROUP,
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
                    print(
                        f"Deleted failed raw demo directory: {failed_dir}",
                        flush=True,
                    )
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
        "group": EXPERIMENT_GROUP,
        "participant_id": participant_id,
        "participant": CONTROL_PARTICIPANTS[participant_id],
        "seed": args.seed,
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
        if summary.get("group") != EXPERIMENT_GROUP:
            raise ValueError(f"Group mismatch in {path}")
        if summary.get("participant_id") != participant_id:
            raise ValueError(f"Participant mismatch in {path}")
        if summary.get("requested_demo_indices") != list(demo_indices):
            raise ValueError(f"Demo-index mismatch in {path}")
        if summary.get("successful_demos") != len(demo_indices):
            raise ValueError(f"Incomplete successful demos in {path}")
        summary["successful_waypoint_spread"] = waypoint_spread(
            [row["spec"]["middle_waypoint"] for row in summary["successes"]]
        )
        write_json(path, summary)
        summaries.append(summary)
    group_summary = {
        "group": EXPERIMENT_GROUP,
        "seed": int(seed),
        "participant_order": list(participant_ids),
        "demo_indices": list(demo_indices),
        "successful_participants": len(summaries),
        "summaries": summaries,
    }
    write_json(output_dir / "summary.json", group_summary)
    return group_summary


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Collect broad, non-converging synthetic Control-participant "
            "obstacle demonstrations"
        )
    )
    parser.add_argument(
        "--participants",
        nargs="+",
        default=list(CONTROL_PARTICIPANTS),
    )
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
        "group": EXPERIMENT_GROUP,
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
