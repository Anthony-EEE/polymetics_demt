#!/usr/bin/env python3
"""Synthetic target-participant obstacle-transport demonstrations.

Each participant has a fixed personal waypoint centre. Across 30 successful
demonstrations, the waypoint sampling envelope contracts toward that centre.
Cube starts retain broad coverage and are shared across participants so that
participant identity is not confounded with start-state difficulty.
"""

import argparse
import json
import math
import shutil
from pathlib import Path

import numpy as np
import pybullet as pb

from main_obstacle_transport import (
    BOX_INITIAL_Z,
    BOX_START_X_BOUNDS,
    BOX_START_Y_BOUNDS,
    EXPERIMENT_GROUP,
    OBSTACLE_XY,
    RELEASE_Z,
    TARGET_XY,
    write_json,
    write_trajectory_plot,
)
from rebuttal_target_pipeline.target_protocol import (
    TARGET_SUCCESS_CRITERION,
    TARGET_XY_TOLERANCE,
    TargetObstacleTransportSim,
)


NUM_DEMOS_PER_PARTICIPANT = 30
WAYPOINT_ROUTE_X_BOUNDS = {"L": (0.10, 0.30), "R": (0.70, 0.90)}
WAYPOINT_Z_BOUNDS = (0.19, 0.29)
CONVERGENCE_TIME_CONSTANT = 8.0
INITIAL_X_RADIUS = 0.10
FINAL_X_RADIUS = 0.02
INITIAL_Z_RADIUS = 0.05
FINAL_Z_RADIUS = 0.01

# Both route means are exactly the nominal waypoint centres: L=(.2,.25,.24)
# and R=(.8,.25,.24). Individual centres are frozen before outcome testing.
TARGET_PARTICIPANTS = {
    "T01": {"route": "L", "center": (0.145, 0.250, 0.220)},
    "T02": {"route": "L", "center": (0.170, 0.250, 0.266)},
    "T03": {"route": "L", "center": (0.200, 0.250, 0.234)},
    "T04": {"route": "L", "center": (0.228, 0.250, 0.213)},
    "T05": {"route": "L", "center": (0.257, 0.250, 0.267)},
    "T06": {"route": "R", "center": (0.742, 0.250, 0.254)},
    "T07": {"route": "R", "center": (0.774, 0.250, 0.212)},
    "T08": {"route": "R", "center": (0.803, 0.250, 0.269)},
    "T09": {"route": "R", "center": (0.832, 0.250, 0.228)},
    "T10": {"route": "R", "center": (0.849, 0.250, 0.237)},
}


def seeded_rng(*components):
    return np.random.default_rng(np.random.SeedSequence([int(value) for value in components]))


def convergence_radii(demo_index):
    if not 0 <= int(demo_index) < NUM_DEMOS_PER_PARTICIPANT:
        raise ValueError(f"demo_index must be in [0, {NUM_DEMOS_PER_PARTICIPANT - 1}]")
    decay = math.exp(-float(demo_index) / CONVERGENCE_TIME_CONSTANT)
    return {
        "x_radius": FINAL_X_RADIUS + (INITIAL_X_RADIUS - FINAL_X_RADIUS) * decay,
        "z_radius": FINAL_Z_RADIUS + (INITIAL_Z_RADIUS - FINAL_Z_RADIUS) * decay,
        "decay": decay,
    }


def shared_cube_start(seed, demo_index, attempt_index=0):
    """Return a shared broad cube start with deterministic replenishment.

    The scripted EE starts at the same x/y as the cube and at box_z + 0.10,
    so the obsolete x<=0.68 proxy for an x+0.10 EE offset is not applicable.
    Attempt zero exactly preserves the authoritative smoke manifest.  If that
    candidate fails the common scripted setup, later attempts draw a new
    30-point Latin-hypercube candidate set from the same frozen broad support.
    The candidate remains shared across participants for a given
    ``(demo_index, attempt_index)``.
    """
    attempt_index = int(attempt_index)
    if attempt_index < 0:
        raise ValueError("attempt_index must be non-negative")
    if attempt_index == 0:
        # Preserve the byte-for-byte authoritative participant manifest.
        rng = seeded_rng(seed, 0x53544152)
    else:
        rng = seeded_rng(seed, 0x53544152, attempt_index, 0x5245504C)
    x_bins = rng.permutation(NUM_DEMOS_PER_PARTICIPANT)
    x_jitter = rng.uniform(0.0, 1.0, size=NUM_DEMOS_PER_PARTICIPANT)
    y_values = rng.uniform(*BOX_START_Y_BOUNDS, size=NUM_DEMOS_PER_PARTICIPANT)
    fraction = (float(x_bins[demo_index]) + float(x_jitter[demo_index])) / NUM_DEMOS_PER_PARTICIPANT
    x = BOX_START_X_BOUNDS[0] + fraction * (BOX_START_X_BOUNDS[1] - BOX_START_X_BOUNDS[0])
    position = [float(x), float(y_values[demo_index]), BOX_INITIAL_Z]
    result = {
        "position": position,
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


def sample_personal_waypoint(participant_id, demo_index, attempt_index, seed, max_draws=1000):
    participant = TARGET_PARTICIPANTS[participant_id]
    route = participant["route"]
    center = np.asarray(participant["center"], dtype=float)
    radii = convergence_radii(demo_index)
    participant_number = int(participant_id[1:])
    rng = seeded_rng(seed, participant_number, demo_index, attempt_index, 0x57505954)
    x_bounds = WAYPOINT_ROUTE_X_BOUNDS[route]
    rejected = 0
    for draw_index in range(int(max_draws)):
        radius = math.sqrt(float(rng.uniform(0.0, 1.0)))
        theta = float(rng.uniform(0.0, 2.0 * math.pi))
        x_delta = radii["x_radius"] * radius * math.cos(theta)
        z_delta = radii["z_radius"] * radius * math.sin(theta)
        candidate = np.asarray(
            [center[0] + x_delta, OBSTACLE_XY[1], center[2] + z_delta],
            dtype=float,
        )
        if x_bounds[0] <= candidate[0] <= x_bounds[1] and WAYPOINT_Z_BOUNDS[0] <= candidate[2] <= WAYPOINT_Z_BOUNDS[1]:
            return candidate, {
                **radii,
                "area_uniform_radius": radius,
                "theta_rad": theta,
                "x_delta": float(x_delta),
                "z_delta": float(z_delta),
                "draw_index": draw_index,
                "rejected_draws": rejected,
                "route_x_bounds": list(x_bounds),
                "z_bounds": list(WAYPOINT_Z_BOUNDS),
            }
        rejected += 1
    raise RuntimeError(
        f"Could not sample bounded waypoint for {participant_id} demo {demo_index}"
    )


def participant_task_spec(participant_id, demo_index, attempt_index, seed):
    participant = TARGET_PARTICIPANTS[participant_id]
    waypoint, sampling = sample_personal_waypoint(
        participant_id,
        demo_index,
        attempt_index,
        seed,
    )
    box_sampling = shared_cube_start(seed, demo_index, attempt_index)
    box = box_sampling["position"]
    return {
        "group": EXPERIMENT_GROUP,
        "participant_id": participant_id,
        "condition": participant["route"],
        "demo_index": int(demo_index),
        "attempt_index": int(attempt_index),
        "box_initial_position": box,
        "scripted_ee_initial_position": [box[0], box[1], box[2] + 0.10],
        "participant_waypoint_center": list(participant["center"]),
        "middle_waypoint": waypoint.tolist(),
        "waypoint_sampling": sampling,
        "transport_z": float(waypoint[2]),
        "release_pose": [TARGET_XY[0], TARGET_XY[1], RELEASE_Z],
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "success_criterion": TARGET_SUCCESS_CRITERION,
        "success_protocol_scope": EXPERIMENT_GROUP,
        "shared_cube_start_manifest": f"seed_{seed}_vertical_start_lhs30",
        "box_start_sampling": box_sampling,
    }


def validate_participant_manifest():
    left = np.asarray([row["center"] for row in TARGET_PARTICIPANTS.values() if row["route"] == "L"])
    right = np.asarray([row["center"] for row in TARGET_PARTICIPANTS.values() if row["route"] == "R"])
    if left.shape != (5, 3) or right.shape != (5, 3):
        raise ValueError("Expected exactly five L and five R target participants")
    if not np.allclose(left.mean(axis=0), [0.20, 0.25, 0.24]):
        raise ValueError(f"L participant centres have wrong mean: {left.mean(axis=0)}")
    if not np.allclose(right.mean(axis=0), [0.80, 0.25, 0.24]):
        raise ValueError(f"R participant centres have wrong mean: {right.mean(axis=0)}")


def write_protocol_preview(output_dir, seed):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "group": EXPERIMENT_GROUP,
        "seed": int(seed),
        "num_demos_per_participant": NUM_DEMOS_PER_PARTICIPANT,
        "participants": TARGET_PARTICIPANTS,
        "shared_cube_starts": [
            shared_cube_start(seed, demo_index)
            for demo_index in range(NUM_DEMOS_PER_PARTICIPANT)
        ],
        "convergence": {
            "time_constant": CONVERGENCE_TIME_CONSTANT,
            "initial_x_radius": INITIAL_X_RADIUS,
            "final_x_radius": FINAL_X_RADIUS,
            "initial_z_radius": INITIAL_Z_RADIUS,
            "final_z_radius": FINAL_Z_RADIUS,
        },
        "candidate_waypoints": {
            participant_id: [
                participant_task_spec(participant_id, demo_index, 0, seed)["middle_waypoint"]
                for demo_index in range(NUM_DEMOS_PER_PARTICIPANT)
            ]
            for participant_id in TARGET_PARTICIPANTS
        },
    }
    write_json(output_dir / "participant_manifest.json", manifest)

    figure, axes = plt.subplots(2, 5, figsize=(16, 7.2), sharey=True, layout="constrained")
    for axis, (participant_id, participant) in zip(axes.flat, TARGET_PARTICIPANTS.items()):
        waypoints = np.asarray(manifest["candidate_waypoints"][participant_id])
        demo_numbers = np.arange(1, NUM_DEMOS_PER_PARTICIPANT + 1)
        scatter = axis.scatter(
            waypoints[:, 0],
            waypoints[:, 2],
            c=demo_numbers,
            cmap="viridis",
            s=34,
            edgecolors="none",
        )
        center = participant["center"]
        axis.scatter(center[0], center[2], marker="*", s=150, color="red", label="personal centre")
        axis.set_title(f"{participant_id} / {participant['route']}")
        axis.set_xlim(WAYPOINT_ROUTE_X_BOUNDS[participant["route"]])
        axis.set_ylim(WAYPOINT_Z_BOUNDS)
        axis.grid(alpha=0.25)
        axis.set_xlabel("waypoint x (m)")
    axes[0, 0].set_ylabel("waypoint z (m)")
    axes[1, 0].set_ylabel("waypoint z (m)")
    figure.colorbar(scatter, ax=axes.ravel().tolist(), label="demonstration index", shrink=0.88)
    figure.suptitle("Synthetic target participants: broad-to-concentrated waypoint sampling")
    figure.savefig(output_dir / "waypoint_convergence.png", dpi=170)
    plt.close(figure)


def collect_participant(args, participant_id, demo_indices):
    participant_dir = args.output_dir / participant_id
    participant_dir.mkdir(parents=True, exist_ok=True)
    sim = TargetObstacleTransportSim(
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
                                "collection_boundary": "after_validated_scripted_grasp_and_lift",
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
                        f"[{participant_id}/{spec['condition']}] demo={demo_index:02d} "
                        f"success waypoint={np.round(spec['middle_waypoint'], 4).tolist()}",
                        flush=True,
                    )
                    break
                if args.save_raw_frames and sim.demo_dir is not None and sim.demo_dir.exists():
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
        "group": EXPERIMENT_GROUP,
        "participant_id": participant_id,
        "participant": TARGET_PARTICIPANTS[participant_id],
        "seed": args.seed,
        "target_xy_tolerance_m": TARGET_XY_TOLERANCE,
        "success_criterion": TARGET_SUCCESS_CRITERION,
        "success_protocol_scope": EXPERIMENT_GROUP,
        "requested_demo_indices": list(demo_indices),
        "successful_demos": len(results),
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
        if summary.get("participant_id") != participant_id:
            raise ValueError(f"Participant mismatch in {path}")
        if summary.get("requested_demo_indices") != list(demo_indices):
            raise ValueError(f"Demo-index mismatch in {path}")
        if summary.get("successful_demos") != len(demo_indices):
            raise ValueError(f"Incomplete successful demos in {path}")
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
        description="Collect converging synthetic target-participant obstacle demonstrations"
    )
    parser.add_argument("--participants", nargs="+", default=list(TARGET_PARTICIPANTS))
    parser.add_argument("--demo-indices", nargs="+", type=int, default=[0])
    parser.add_argument("--all-30", action="store_true")
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--max-attempts-per-demo", type=int, default=10)
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
    unknown = sorted(set(args.participants) - set(TARGET_PARTICIPANTS))
    if unknown:
        raise ValueError(f"Unknown participants: {unknown}")
    demo_indices = list(range(NUM_DEMOS_PER_PARTICIPANT)) if args.all_30 else sorted(set(args.demo_indices))
    if not demo_indices or min(demo_indices) < 0 or max(demo_indices) >= NUM_DEMOS_PER_PARTICIPANT:
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
