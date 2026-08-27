#!/usr/bin/env python3
"""Freeze Control configs through the exact frozen Target training helper."""

import hashlib
import json
import sys
from pathlib import Path


EXAMPLES_DIR = Path(__file__).resolve().parents[1]
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from rebuttal_target_pipeline import prepare_target_training as implementation  # noqa: E402


EXPECTED_IMPLEMENTATION_SHA256 = (
    "2ffb5e9f11a7bf991ae62ea05d6ad9e33ca95ccc7025086afab7f63815bf8af9"
)
GROUP = "simulation_control_group"
PARTICIPANTS = [f"C{index:02d}" for index in range(1, 11)]
REPO_ROOT = EXAMPLES_DIR.parent
TARGET_MODELS_ROOT = (
    REPO_ROOT / "rebuttal_dataset/simulation_target_group/models"
)
EXPECTED_TARGET_MANIFEST_SHA256 = (
    "610caef20d78f441df533aa2b1951029006cdf7b1d5aabf37c8bb1fdde8a5623"
)
EXPECTED_UNIFORM_PROTOCOL_SHA256 = (
    "db0aca893cf5554b01b13c8937af49cc83d9a1024f4038007d4182f21df1b0c6"
)


def main():
    actual = hashlib.sha256(Path(implementation.__file__).read_bytes()).hexdigest()
    if actual != EXPECTED_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "Frozen Target training-preparation helper changed: "
            f"expected {EXPECTED_IMPLEMENTATION_SHA256}, observed {actual}"
        )
    target_manifest_path = TARGET_MODELS_ROOT / "training_experiment_manifest.json"
    target_manifest_hash = hashlib.sha256(target_manifest_path.read_bytes()).hexdigest()
    if target_manifest_hash != EXPECTED_TARGET_MANIFEST_SHA256:
        raise RuntimeError(
            "Frozen Target training manifest changed: "
            f"expected {EXPECTED_TARGET_MANIFEST_SHA256}, observed {target_manifest_hash}"
        )
    target_manifest = json.loads(target_manifest_path.read_text(encoding="utf-8"))
    if (
        target_manifest.get("uniform_training_protocol_sha256")
        != EXPECTED_UNIFORM_PROTOCOL_SHA256
    ):
        raise RuntimeError("Frozen Target uniform training protocol hash changed")

    implementation.GROUP = GROUP
    implementation.PARTICIPANTS = PARTICIPANTS
    original_canonical_protocol = implementation.canonical_protocol

    def target_hash_compatible_protocol(config):
        """Exclude only the group-owned output location from protocol identity.

        The frozen Target helper already masks participant name and HDF5 path,
        but its historical hash includes Target's operational runs directory.
        Map the Control runs path to that historical string only in the copied
        value used for hashing; the executable Control config is unchanged.
        """
        value = original_canonical_protocol(config)
        output_dir = Path(value["train"]["output_dir"]).resolve()
        if output_dir.parts[-3:] != (GROUP, "models", "runs"):
            raise RuntimeError(
                f"Unexpected Control training output directory: {output_dir}"
            )
        value["train"]["output_dir"] = str(
            (TARGET_MODELS_ROOT / "runs").resolve()
        )
        return value

    implementation.canonical_protocol = target_hash_compatible_protocol
    try:
        implementation.main()
    finally:
        implementation.canonical_protocol = original_canonical_protocol

    try:
        models_root = Path(sys.argv[sys.argv.index("--models-root") + 1]).resolve()
    except (ValueError, IndexError) as exc:
        raise RuntimeError("Missing --models-root for Control training preparation") from exc
    manifest = json.loads(
        (models_root / "training_experiment_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if manifest.get("uniform_training_protocol_sha256") != EXPECTED_UNIFORM_PROTOCOL_SHA256:
        raise RuntimeError("Control training protocol does not match frozen Target hash")
    expected_runs_root = (models_root / "runs").resolve()
    for participant_id in PARTICIPANTS:
        config = json.loads(
            (models_root / "configs" / f"{participant_id}.json").read_text(
                encoding="utf-8"
            )
        )
        if Path(config["train"]["output_dir"]).resolve() != expected_runs_root:
            raise RuntimeError(
                f"{participant_id} executable config escaped the Control runs root"
            )


if __name__ == "__main__":
    main()
