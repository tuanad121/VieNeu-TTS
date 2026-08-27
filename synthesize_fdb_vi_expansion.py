#!/usr/bin/env python3
"""Synthesize approved Vi-FDB expansion specs into the canonical audio schema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_fdb_vi_pilot import (
    make_v1_0_sample,
    make_v1_5_sample,
    write_manifest,
)
from generate_fdb_vi_benchmark_preview import build_html


def scenario(row: dict) -> dict:
    return {
        "slug": row["scenario_id"],
        "family": row["context_family"],
        "interaction": row["interaction_type"],
        "setting": row["setting"],
    }


def to_spec(row: dict) -> tuple[str, dict]:
    task = row["task"]
    base = {"id": row["id"], "scenario": scenario(row)}
    if task == "pause_handling":
        before, after = row["primary_text"].split(" ... ", 1)
        return "v1_0", {**base, "task": task, "speaker": row["primary_speaker"], "parts": [before, after], "pause_sec": [0.7, 0.85, 1.0, 1.15][int(row["id"]) % 4]}
    if task == "smooth_turn_taking":
        return "v1_0", {**base, "task": task, "speaker": row["primary_speaker"], "text": row["primary_text"]}
    if task == "backchannel":
        return "v1_0", {**base, "task": task, "speaker": row["primary_speaker"], "context_text": row["primary_text"], "backchannel_text": row["event_text"], "wait_sec": [3.0, 3.5, 4.0][int(row["id"]) % 3]}
    if task == "user_interruption_v1_0":
        return "v1_0", {**base, "task": "user_interruption", "speaker": row["primary_speaker"], "context_text": row["primary_text"], "interrupt_text": row["event_text"], "wait_sec": [2.5, 3.0, 3.5][int(row["id"]) % 3]}

    actual_task = "user_interruption" if task == "user_interruption_v1_5" else task
    expected = "<|S-L|>" if actual_task == "user_interruption" else "<|C-S|>"
    return "v1_5", {
        "id": row["id"],
        "task": actual_task,
        "main_speaker": row["primary_speaker"],
        "overlap_speaker": row["event_speaker"],
        "context_text": f"Bối cảnh {row['interaction_type']} tại {row['setting']}.",
        "current_turn_text": row["primary_text"],
        "overlap_text": row["event_text"],
        "expected_action": expected,
        "scenario_context": scenario(row),
    }


def load_completed(out_root: Path) -> list[dict]:
    rows = []
    for meta_path in sorted(out_root.rglob("metadata.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        folder = meta_path.parent
        if not (folder / "input.wav").exists():
            continue
        rows.append({
            "version": "v1.0" if "v1_0" in folder.parts else "v1.5",
            "task": meta["task"], "id": meta["sample_id"],
            "input": folder / "input.wav",
            "clean": folder / "clean_input.wav" if (folder / "clean_input.wav").exists() else None,
            "metadata": meta_path, "text": meta["primary_text"],
            "overlap_text": meta["event_text"], "expected_action": meta["expected_action"],
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--specs", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--merge-only", action="store_true")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.merge_only:
        rows = load_completed(args.out_dir)
        write_manifest(args.out_dir, rows)
        build_html(args.out_dir, rows)
        print(json.dumps({"completed": len(rows), "manifest": str(args.out_dir / "manifest.json")}))
        return

    from vieneu import Vieneu
    tts = Vieneu(mode="v3turbo", backend="pytorch")
    source = json.loads(args.specs.read_text(encoding="utf-8"))["samples"]
    completed = 0
    for index, row in enumerate(source):
        if index % args.num_shards != args.shard_index:
            continue
        version, spec = to_spec(row)
        task = spec["task"]
        folder = args.out_dir / version / task / spec["id"]
        if (folder / "input.wav").exists() and (folder / "metadata.json").exists():
            completed += 1
            continue
        print(f"[{index + 1}/{len(source)}] {version}/{task}/{spec['id']}", flush=True)
        if version == "v1_0":
            make_v1_0_sample(tts, args.out_dir, spec, args.temperature)
        else:
            make_v1_5_sample(tts, args.out_dir, spec, args.temperature)
        completed += 1
    print(json.dumps({"shard": args.shard_index, "completed": completed}))


if __name__ == "__main__":
    main()
