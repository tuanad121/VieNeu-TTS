from __future__ import annotations

from pathlib import Path
import argparse
import json
import re

import soundfile as sf
from datasets import load_dataset
from huggingface_hub import hf_hub_download

from build_reference_screening import build_html


BAD_TOKENS = {
    "creative", "notion", "pandamic", "facebook", "instagram", "messenger",
    "follow", "ship", "harvard", "goal", "ok", "ceo", "youtube", "asmr",
}


def vietnamese_ratio(text: str) -> float:
    chars = [c for c in text.lower() if c.isalpha()]
    if not chars:
        return 0.0
    vi_chars = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
    return sum(1 for c in chars if c in vi_chars) / len(chars)


def looks_reasonable(row: dict) -> bool:
    duration = float(row.get("duration") or 0)
    if duration < 5.0 or duration > 12.0:
        return False
    text = str(row.get("text") or "")
    lower = text.lower()
    if any(tok in lower for tok in BAD_TOKENS):
        return False
    if vietnamese_ratio(text) < 0.08:
        return False
    words = text.split()
    if len(words) < 12:
        return False
    return True


def safe_id(index: int, source: str) -> str:
    base = re.sub(r"[^A-Za-z0-9]+", "_", source).strip("_")[:48]
    return f"cand_{index:02d}_{base}"


def trim_wav(src: Path, dst: Path, seconds: float) -> None:
    audio, sr = sf.read(src)
    sf.write(dst, audio[: int(sr * seconds)], sr)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/fdb_vi_reference_screening")
    parser.add_argument("--count", type=int, default=24)
    parser.add_argument("--max-scan", type=int, default=2500)
    parser.add_argument("--trim-seconds", type=float, default=6.0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    refs_dir = out_dir / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)

    ds = load_dataset("thanhnew2001/VietSuperSpeech", split="validation", streaming=True)
    selected = []
    seen_sources = set()
    for row_idx, row in enumerate(ds):
        if row_idx >= args.max_scan:
            break
        source = row.get("source") or ""
        if source in seen_sources:
            continue
        if not looks_reasonable(row):
            continue
        seen_sources.add(source)
        selected.append(row)
        if len(selected) >= args.count:
            break

    manifest = {"references": []}
    for i, row in enumerate(selected, start=1):
        ref_id = safe_id(i, row["source"])
        local_ref = refs_dir / f"{ref_id}.wav"
        source_path = Path(
            hf_hub_download("thanhnew2001/VietSuperSpeech", filename=row["audio"], repo_type="dataset")
        )
        trim_wav(source_path, local_ref, args.trim_seconds)
        manifest["references"].append(
            {
                "id": ref_id,
                "file": str(local_ref.relative_to(out_dir)),
                "source": row["source"],
                "text": row["text"],
                "duration": row["duration"],
                "dataset_audio": row["audio"],
            }
        )
        print(ref_id, row["duration"], row["source"])

    manifest_path = out_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    (out_dir / "index.html").write_text(build_html(manifest), encoding="utf-8")
    print(out_dir / "index.html")


if __name__ == "__main__":
    main()
