import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "examples"))

import eval_abla1_trained_policies as position  # noqa: E402
import eval_orn_mvp_trained_policies as contact  # noqa: E402
from rollout_contract import (  # noqa: E402
    checkpoints_from_manifest,
    paired_discordances,
    stream_seed,
    validate_rollout_files,
)


def protocol_args(num_rollouts=50):
    return SimpleNamespace(
        seed=628,
        num_rollouts=num_rollouts,
        horizon=200,
        sample_hz=8.0,
        action_gap=2,
        action_dt=0.25,
        terminate_on_success=True,
        success_lift_height=0.20,
        num_points=10000,
        random_start_x_min=0.2,
        random_start_x_max=0.6,
        random_start_z_min=0.2,
        random_start_z_max=0.6,
        shared_start_radius_min=0.0,
        shared_start_radius=0.35,
        corridor_start_max_error=0.025,
        corridor_start_center=[0.3, 0.0, 0.5],
    )


class PositionContactN50Test(unittest.TestCase):
    def test_rng_streams_are_deterministic_and_separate(self):
        runtime = [stream_seed(628, i, 0x52554E) for i in range(50)]
        pointcloud = [stream_seed(628, i, 0x504344) for i in range(50)]
        self.assertEqual(len(set(runtime)), 50)
        self.assertEqual(len(set(pointcloud)), 50)
        self.assertTrue(all(a != b for a, b in zip(runtime, pointcloud)))
        self.assertEqual(runtime, [stream_seed(628, i, 0x52554E) for i in range(50)])

    def test_contact_manifest_common_latent_mapping_and_distinct_starts(self):
        args = protocol_args()
        rows = []
        for i in range(50):
            u = (i + 0.5) / 50.0
            axis = [1.0, 0.0, 0.0]
            orientations = {}
            for condition, maximum in contact.ORN_CONDITIONS.items():
                orientations[condition] = {
                    "orientation_angle_degrees": (2.0 * u - 1.0) * maximum,
                    "manifest_start_ik_validation": {"realised_error": 0.0},
                }
            rows.append(
                {
                    "rollout_index": i,
                    "random_start": [0.2 + i * 0.007, 0.0, 0.6 - i * 0.007],
                    "orientation_axis": axis,
                    "common_u": u,
                    "condition_orientations": orientations,
                    "rng_seed": stream_seed(628, i, 0x52554E),
                    "point_cloud_rng_seed": stream_seed(628, i, 0x504344),
                }
            )
        manifest = {
            "condition_order": list(contact.CONDITION_ORDER),
            "protocol": contact.evaluation_protocol(args),
            "rollouts": rows,
        }
        self.assertEqual(contact.validate_paired_manifest(args, manifest), rows)
        self.assertTrue(all(row["condition_orientations"]["R00"]["orientation_angle_degrees"] == 0.0 for row in rows))
        bad = json.loads(json.dumps(manifest))
        bad["rollouts"][1]["random_start"] = bad["rollouts"][0]["random_start"]
        with self.assertRaisesRegex(ValueError, "distinct"):
            contact.validate_paired_manifest(args, bad)

    def test_position_manifest_rejects_wrong_condition_set(self):
        args = protocol_args(1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps({"condition_order": ["S15"], "protocol": position.evaluation_protocol(args), "shared_corridor_starts": [[0.3, 0, 0.5]], "shared_start_records": [{}]}))
            with self.assertRaisesRegex(ValueError, "condition_order"):
                position.load_start_manifest(args, path)

    def test_checkpoint_manifest_hash_matching(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            checkpoint = directory / "model_epoch_40.pth"
            checkpoint.write_bytes(b"checkpoint")
            import hashlib
            digest = hashlib.sha256(b"checkpoint").hexdigest()
            manifest = directory / "checkpoints.json"
            manifest.write_text(json.dumps({"condition_order": ["A"], "checkpoints": {"A": {"path": str(checkpoint), "sha256": digest}}}))
            _, resolved = checkpoints_from_manifest(manifest, ("A",), ("A",))
            self.assertEqual(resolved["A"], checkpoint)
            payload = json.loads(manifest.read_text())
            payload["checkpoints"]["A"]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                checkpoints_from_manifest(manifest, ("A",), ("A",))

    def test_paired_tables_sum_to_fifty(self):
        summaries = {
            "A": {"rollouts": [{"success": i % 2 == 0} for i in range(50)]},
            "B": {"rollouts": [{"success": i % 3 == 0} for i in range(50)]},
        }
        table = paired_discordances(("A", "B"), summaries)["A_vs_B"]
        self.assertEqual(sum(table.values()), 50)

    def test_merge_rejects_stale_or_partial_rollout_jsons(self):
        rows = [{"rollout_index": 0}, {"rollout_index": 1}]
        with tempfile.TemporaryDirectory() as directory:
            rollout_dir = Path(directory) / "rollouts" / "A"
            rollout_dir.mkdir(parents=True)
            for index, row in enumerate(rows):
                (rollout_dir / f"rollout_{index:03d}.json").write_text(json.dumps(row))
            validate_rollout_files(directory, "A", 2, rows)
            (rollout_dir / "rollout_999.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "stale"):
                validate_rollout_files(directory, "A", 2, rows)


if __name__ == "__main__":
    unittest.main()
