#!/usr/bin/env python3
"""Materialize four 30-demo raw groups from the common successful candidates."""

import argparse
import json
import os
from pathlib import Path


CONDITIONS = ("VR1P5", "V050_200", "VR3", "VR4")


def demo_index(path):
    return int(path.name.split("_", 1)[1])


def successful_candidates(path):
    records = {}
    for demo_dir in sorted(path.glob("demo_*"), key=demo_index):
        metadata_path = demo_dir / "metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (metadata.get("success") or {}).get("success") is not True:
            continue
        candidate_id = metadata.get("candidate_id")
        if not candidate_id:
            raise ValueError(f"{metadata_path}: missing candidate_id")
        if candidate_id in records:
            raise ValueError(f"{path}: duplicate candidate_id {candidate_id}")
        records[candidate_id] = demo_dir.resolve()
    return records


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--attempt-template", default="attempts_temporal_{condition}_seed1")
    parser.add_argument("--output-template", default="temporal_{condition}_d30_seed1")
    parser.add_argument("--num-demos", type=int, default=30)
    parser.add_argument("--selection-output", type=Path, default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    records = {
        condition: successful_candidates(
            args.root / args.attempt_template.format(condition=condition)
        )
        for condition in CONDITIONS
    }
    common = set.intersection(*(set(records[condition]) for condition in CONDITIONS))
    selected = sorted(common)[: args.num_demos]
    if len(selected) != args.num_demos:
        counts = {condition: len(value) for condition, value in records.items()}
        raise RuntimeError(
            f"Only {len(selected)}/{args.num_demos} common successful candidates; "
            f"per-condition successes={counts}"
        )

    for condition in CONDITIONS:
        output_dir = args.root / args.output_template.format(condition=condition)
        if output_dir.exists() and any(output_dir.iterdir()):
            raise FileExistsError(f"Refusing to overwrite non-empty final raw group: {output_dir}")
        output_dir.mkdir(parents=True, exist_ok=True)
        for demo_index_value, candidate_id in enumerate(selected):
            link = output_dir / f"demo_{demo_index_value}"
            target = records[condition][candidate_id]
            os.symlink(target, link, target_is_directory=True)

    selection_path = args.selection_output or (args.root / "selected_candidates.json")
    selection = {
        "schema_version": 1,
        "condition_order": list(CONDITIONS),
        "num_selected": len(selected),
        "candidate_ids": selected,
        "selection_rule": "lexicographically first 30 candidate IDs successful in all four conditions",
        "attempt_groups": {
            condition: str((args.root / args.attempt_template.format(condition=condition)).resolve())
            for condition in CONDITIONS
        },
        "final_groups": {
            condition: str((args.root / args.output_template.format(condition=condition)).resolve())
            for condition in CONDITIONS
        },
    }
    selection_path.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {selection_path}; selected {len(selected)} common successful candidates")


if __name__ == "__main__":
    main()
