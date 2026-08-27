from __future__ import annotations

from pathlib import Path
import argparse
import html
import json
import shutil


SPEAKERS = {
    "north_female": "src/vieneu/assets/samples/Ly (nữ miền Bắc).wav",
    "north_male": "src/vieneu/assets/samples/Bình (nam miền Bắc).wav",
    "south_female": "src/vieneu/assets/samples/Đoan (nữ miền Nam).wav",
    "south_male": "src/vieneu/assets/samples/Vĩnh (nam miền Nam).wav",
}


ENGLISH_EXAMPLES = {
    "pause_handling": {
        "label": "English FDB v1.0 pause handling",
        "input": "v1_v1.5/evaluation/example_data/pause_handling_example/1/input.wav",
        "metadata": "v1_v1.5/evaluation/example_data/pause_handling_example/1/pause.json",
    },
    "smooth_turn_taking": {
        "label": "English FDB v1.0 smooth turn-taking",
        "input": "v1_v1.5/evaluation/example_data/smooth_turn_taking_example/1/input.wav",
        "metadata": "v1_v1.5/evaluation/example_data/smooth_turn_taking_example/1/turn_taking.json",
    },
    "user_interruption": {
        "label": "English FDB v1.0 user interruption",
        "input": "v1_v1.5/evaluation/example_data/user_interruption_example/1/input.wav",
        "metadata": "v1_v1.5/evaluation/example_data/user_interruption_example/1/interrupt.json",
    },
}


V1_0_SAMPLES = [
    {
        "id": "000001",
        "task": "pause_handling",
        "speaker": "north_female",
        "parts": [
            "Ờ, mình muốn đặt một phòng đôi gần Hồ Gươm",
            "cho tối thứ bảy này, còn phòng nào yên tĩnh không?",
        ],
        "pause_sec": 0.85,
    },
    {
        "id": "000001",
        "task": "smooth_turn_taking",
        "speaker": "north_male",
        "text": "Bạn kiểm tra giúp mình lịch hẹn khám tổng quát vào sáng mai được không?",
    },
    {
        "id": "000001",
        "task": "user_interruption",
        "speaker": "north_female",
        "context_text": "Bạn gợi ý giúp mình vài hoạt động thư giãn ở Hà Nội cuối tuần này được không?",
        "interrupt_text": "À khoan, mình đổi ý rồi. Mình muốn tìm lớp học nấu ăn cho hai người.",
        "wait_sec": 3.0,
    },
]


V1_5_SAMPLES = [
    {
        "id": "000001",
        "task": "user_interruption",
        "main_speaker": "north_female",
        "overlap_speaker": "north_female",
        "context_text": "Mình đang hỏi thông tin đặt phòng khách sạn.",
        "current_turn_text": "Bạn xem giúp mình phòng đôi ở Đà Nẵng cuối tuần này còn không nhé.",
        "overlap_text": "À khoan, mình đổi sang phòng gia đình cho bốn người nhé.",
        "insert_ratio": 1.0,
        "gain": 1.0,
        "expected_action": "<|S-L|>",
    },
    {
        "id": "000001",
        "task": "user_backchannel",
        "main_speaker": "north_male",
        "overlap_speaker": "north_female",
        "context_text": "Nhân viên lễ tân đang giải thích các lựa chọn đặt xe.",
        "current_turn_text": "Từ sảnh khách sạn ra sân bay thì có xe riêng, xe ghép, hoặc taxi công nghệ.",
        "overlap_text": "Vâng, đúng rồi ạ.",
        "insert_ratio": 0.48,
        "gain": 0.8,
        "expected_action": "<|C-S|>",
    },
    {
        "id": "000001",
        "task": "talking_to_other",
        "main_speaker": "south_female",
        "overlap_speaker": "north_female",
        "context_text": "Khách đang hỏi robot lễ tân về thủ tục nhận phòng.",
        "current_turn_text": "Mình cần đưa căn cước và mã đặt phòng cho quầy lễ tân trước đúng không?",
        "overlap_text": "Chị ơi, lấy giúp em cái ví trong túi với.",
        "insert_ratio": 0.5,
        "gain": 0.75,
        "expected_action": "<|C-S|>",
    },
    {
        "id": "000001",
        "task": "background_speech",
        "main_speaker": "north_female",
        "overlap_speaker": "south_male",
        "context_text": "Khách hỏi robot tiếp tân trong sảnh đông người.",
        "current_turn_text": "Bạn chỉ giúp mình đường tới phòng hội nghị tầng ba được không?",
        "overlap_text": "Mọi người chú ý, thang máy bên trái đang bảo trì trong mười phút.",
        "insert_ratio": 0.35,
        "gain": 0.38,
        "expected_action": "<|C-S|>",
    },
]


def read_audio(path: Path) -> tuple[np.ndarray, int]:
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(path)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return audio.astype(np.float32), sr


def write_audio(path: Path, audio: np.ndarray, sr: int) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
    if peak > 0.98:
        audio = audio / peak * 0.98
    sf.write(path, audio, sr)


def silence(seconds: float, sr: int) -> np.ndarray:
    import numpy as np

    return np.zeros(int(round(seconds * sr)), dtype=np.float32)


def duration(path: Path) -> float:
    import soundfile as sf

    info = sf.info(path)
    return info.frames / float(info.samplerate)


def mix_at(base: np.ndarray, overlay: np.ndarray, sr: int, start_sec: float, gain: float) -> np.ndarray:
    import numpy as np

    start = int(round(start_sec * sr))
    end = start + len(overlay)
    out_len = max(len(base), end)
    out = np.zeros(out_len, dtype=np.float32)
    out[: len(base)] += base
    out[start:end] += overlay * gain
    return out


def synth(tts: Vieneu, text: str, ref_audio: Path, out_path: Path, temperature: float) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio = tts.infer(text, ref_audio=str(ref_audio), temperature=temperature)
    tts.save(audio, str(out_path))
    return out_path


def make_v1_0(tts: Vieneu, out_root: Path, temperature: float) -> list[dict]:
    import numpy as np

    rows = []
    for spec in V1_0_SAMPLES:
        sample_dir = out_root / "v1_0" / spec["task"] / spec["id"]
        stream_dir = sample_dir / "source_streams"
        ref = Path(SPEAKERS[spec["speaker"]])
        sample_dir.mkdir(parents=True, exist_ok=True)

        if spec["task"] == "pause_handling":
            part_paths = [
                synth(tts, part, ref, stream_dir / f"part_{idx}.wav", temperature)
                for idx, part in enumerate(spec["parts"], start=1)
            ]
            part_1, sr = read_audio(part_paths[0])
            part_2, sr_2 = read_audio(part_paths[1])
            if sr != sr_2:
                raise ValueError("Mismatched sample rates from TTS")
            pause_start = len(part_1) / sr
            pause_end = pause_start + float(spec["pause_sec"])
            final = np.concatenate([part_1, silence(spec["pause_sec"], sr), part_2, silence(0.5, sr)])
            write_audio(sample_dir / "input.wav", final, sr)
            annotation = [{"text": "[PAUSE]", "timestamp": [round(pause_start, 3), round(pause_end, 3)]}]
            (sample_dir / "pause.json").write_text(json.dumps(annotation, ensure_ascii=False, indent=2), encoding="utf-8")
            display_text = f"{spec['parts'][0]} ... {spec['parts'][1]}"
        elif spec["task"] == "smooth_turn_taking":
            wav_path = synth(tts, spec["text"], ref, stream_dir / "main.wav", temperature)
            audio, sr = read_audio(wav_path)
            turn_start = len(audio) / sr
            final = np.concatenate([audio, silence(0.6, sr)])
            write_audio(sample_dir / "input.wav", final, sr)
            annotation = [{"text": "[TURN-TAKING]", "timestamp": [round(turn_start, 3), round(turn_start + 0.4, 3)]}]
            (sample_dir / "turn_taking.json").write_text(json.dumps(annotation, ensure_ascii=False, indent=2), encoding="utf-8")
            display_text = spec["text"]
        else:
            context_path = synth(tts, spec["context_text"], ref, stream_dir / "context.wav", temperature)
            interrupt_path = synth(tts, spec["interrupt_text"], ref, stream_dir / "interrupt.wav", temperature)
            context_audio, sr = read_audio(context_path)
            interrupt_audio, sr_2 = read_audio(interrupt_path)
            if sr != sr_2:
                raise ValueError("Mismatched sample rates from TTS")
            wait_sec = float(spec["wait_sec"])
            interrupt_start = len(context_audio) / sr + wait_sec
            interrupt_end = interrupt_start + len(interrupt_audio) / sr
            final = np.concatenate([context_audio, silence(wait_sec, sr), interrupt_audio, silence(0.6, sr)])
            write_audio(sample_dir / "context.wav", context_audio, sr)
            write_audio(sample_dir / "interrupt.wav", interrupt_audio, sr)
            write_audio(sample_dir / "input.wav", final, sr)
            annotation = [
                {
                    "context": spec["context_text"],
                    "interrupt": spec["interrupt_text"],
                    "timestamp": [round(interrupt_start, 3), round(interrupt_end, 3)],
                }
            ]
            (sample_dir / "interrupt.json").write_text(json.dumps(annotation, ensure_ascii=False, indent=2), encoding="utf-8")
            display_text = f"{spec['context_text']} ... {spec['interrupt_text']}"

        metadata_name = {
            "pause_handling": "pause.json",
            "smooth_turn_taking": "turn_taking.json",
            "user_interruption": "interrupt.json",
        }[spec["task"]]
        expected_action = {
            "pause_handling": "<|C-L|>",
            "smooth_turn_taking": "<|S-S|>",
            "user_interruption": "<|S-L|>",
        }[spec["task"]]

        rows.append(
            {
                "version": "v1.0",
                "task": spec["task"],
                "id": spec["id"],
                "dir": sample_dir,
                "input": sample_dir / "input.wav",
                "clean": None,
                "metadata": sample_dir / metadata_name,
                "text": display_text,
                "expected_action": expected_action,
            }
        )
    return rows


def make_v1_5(tts: Vieneu, out_root: Path, temperature: float) -> list[dict]:
    import numpy as np

    rows = []
    for spec in V1_5_SAMPLES:
        sample_dir = out_root / "v1_5" / spec["task"] / spec["id"]
        stream_dir = sample_dir / "source_streams"
        main_ref = Path(SPEAKERS[spec["main_speaker"]])
        overlap_ref = Path(SPEAKERS[spec["overlap_speaker"]])

        main_path = synth(tts, spec["current_turn_text"], main_ref, stream_dir / "main_user.wav", temperature)
        overlap_path = synth(tts, spec["overlap_text"], overlap_ref, stream_dir / "overlap.wav", temperature)
        main_audio, sr = read_audio(main_path)
        overlap_audio, sr_2 = read_audio(overlap_path)
        if sr != sr_2:
            raise ValueError("Mismatched sample rates from TTS")

        main_duration = len(main_audio) / sr
        overlap_duration = len(overlap_audio) / sr
        if spec["task"] == "user_interruption":
            wait_sec = 2.0
            insert_at = main_duration + wait_sec
            clean = np.concatenate([main_audio, silence(wait_sec + overlap_duration + 0.4, sr)])
            mixed = np.concatenate([main_audio, silence(wait_sec, sr), overlap_audio, silence(0.4, sr)])
        else:
            latest_start = max(0.2, main_duration - min(0.6, main_duration * 0.15))
            insert_at = min(max(0.45, main_duration * float(spec["insert_ratio"])), latest_start)
            clean = np.concatenate([main_audio, silence(0.4, sr)])
            mixed = np.concatenate([mix_at(main_audio, overlap_audio, sr, insert_at, float(spec["gain"])), silence(0.4, sr)])

        write_audio(sample_dir / "clean_input.wav", clean, sr)
        write_audio(sample_dir / "input.wav", mixed, sr)

        metadata = {
            "context_text": spec["context_text"],
            "current_turn_text": spec["current_turn_text"],
            "overlap_text": spec["overlap_text"],
            "timestamps": [round(insert_at, 3), round(insert_at + overlap_duration, 3)],
            "scenario": spec["task"],
            "expected_action": spec["expected_action"],
            "main_speaker": spec["main_speaker"],
            "overlap_speaker": spec["overlap_speaker"],
        }
        (sample_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(
            {
                "version": "v1.5",
                "task": spec["task"],
                "id": spec["id"],
                "dir": sample_dir,
                "input": sample_dir / "input.wav",
                "clean": sample_dir / "clean_input.wav",
                "metadata": sample_dir / "metadata.json",
                "text": spec["current_turn_text"],
                "overlap_text": spec["overlap_text"],
                "expected_action": spec["expected_action"],
            }
        )
    return rows


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def copy_english_examples(out_root: Path, repo_root: Path) -> dict[tuple[str, str], list[dict]]:
    copied: dict[tuple[str, str], list[dict]] = {}
    english_root = out_root / "english_examples"
    for task, spec in ENGLISH_EXAMPLES.items():
        task_dir = english_root / task
        input_src = repo_root / spec["input"]
        metadata_src = repo_root / spec["metadata"]
        if not input_src.exists() or not metadata_src.exists():
            continue
        task_dir.mkdir(parents=True, exist_ok=True)
        input_dst = task_dir / "input.wav"
        metadata_dst = task_dir / metadata_src.name
        shutil.copy2(input_src, input_dst)
        shutil.copy2(metadata_src, metadata_dst)
        copied[("v1.0", task)] = [{
            "label": spec["label"],
            "input": input_dst,
            "clean": None,
            "metadata": metadata_dst,
            "metadata_json": json.loads(metadata_dst.read_text(encoding="utf-8")),
        }]
    v15_root = out_root / "english_examples_v15"
    for task_dir in sorted(v15_root.iterdir()) if v15_root.exists() else []:
        if not task_dir.is_dir():
            continue
        pool = []
        for sample_dir in sorted(task_dir.iterdir(), key=lambda path: int(path.name)):
            input_path = sample_dir / "input.wav"
            clean_path = sample_dir / "clean_input.wav"
            metadata_path = sample_dir / "metadata.json"
            if not (input_path.exists() and clean_path.exists() and metadata_path.exists()):
                continue
            pool.append({
                "label": f"English FDB v1.5 {task_dir.name.replace('_', ' ')} — sample {sample_dir.name}",
                "input": input_path,
                "clean": clean_path,
                "metadata": metadata_path,
                "metadata_json": json.loads(metadata_path.read_text(encoding="utf-8")),
            })
        if pool:
            copied[("v1.5", task_dir.name)] = pool
    return copied


def load_existing_rows(out_root: Path) -> list[dict]:
    manifest_path = out_root / "manifest.json"
    rows = []
    for item in json.loads(manifest_path.read_text(encoding="utf-8")):
        metadata_path = out_root / item["metadata"]
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if isinstance(metadata, dict):
            text = metadata.get("primary_text") or metadata.get("current_turn_text") or metadata.get("context_text", "")
            overlap_text = metadata.get("event_text") or metadata.get("overlap_text") or metadata.get("backchannel_text", "")
        else:
            text = metadata[0].get("text", "") if metadata else ""
            overlap_text = ""
        rows.append(
            {
                "version": item["version"],
                "task": item["task"],
                "id": item["id"],
                "dir": metadata_path.parent,
                "input": out_root / item["input"],
                "clean": out_root / item["clean_input"] if item.get("clean_input") else None,
                "metadata": metadata_path,
                "text": text,
                "overlap_text": overlap_text,
                "expected_action": item["expected_action"],
            }
        )
    return rows


def build_html(out_root: Path, rows: list[dict], filename: str = "index.html", page_title: str = "Vietnamese FDB Benchmark Review") -> None:
    repo_root = Path(__file__).resolve().parents[2]
    english_examples = copy_english_examples(out_root, repo_root)
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f7f7f4; color: #202428; }
    h1 { margin: 0 0 8px; }
    .note { color: #5f6870; max-width: 980px; line-height: 1.45; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 14px; margin-top: 18px; }
    .card { background: #fff; border: 1px solid #d8d8d2; border-radius: 8px; padding: 14px; }
    .title { font-size: 18px; font-weight: 800; margin-bottom: 8px; }
    .badge { display: inline-block; border: 1px solid #bdc5cc; border-radius: 999px; padding: 2px 8px; margin-right: 5px; color: #44505a; font-size: 12px; }
    audio { width: 100%; margin: 6px 0 10px; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f1f2ed; padding: 9px; border-radius: 6px; font-size: 12px; }
    .label { font-weight: 700; color: #30363d; margin-top: 10px; }
    .text { color: #59636d; line-height: 1.35; }
    .compare { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 10px; }
    .pane { border: 1px solid #e0e0da; border-radius: 6px; padding: 10px; background: #fbfbf8; }
    .missing { color: #7a4f00; background: #fff7dc; border: 1px solid #e7cf89; padding: 8px; border-radius: 6px; }
    .timebar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin: 4px 0 10px; color: #44505a; font-size: 13px; }
    .timebar button { border: 1px solid #bdc5cc; background: white; border-radius: 5px; padding: 4px 7px; cursor: pointer; font-weight: 650; }
    .timebar button:hover { background: #eef4ff; }
    .now { font-variant-numeric: tabular-nums; min-width: 72px; }
    .toolbar { position: sticky; top: 0; z-index: 10; display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 16px 0; padding: 12px; background: rgba(247,247,244,.96); border: 1px solid #d8d8d2; border-radius: 8px; }
    .toolbar select, .toolbar button, .review button, .review input { border: 1px solid #bdc5cc; border-radius: 5px; background: white; padding: 7px 9px; }
    .toolbar button, .review button { cursor: pointer; font-weight: 700; }
    .progress { margin-left: auto; font-weight: 750; font-variant-numeric: tabular-nums; }
    .review { margin-top: 12px; padding-top: 11px; border-top: 1px solid #e0e0da; }
    .review-actions { display: flex; flex-wrap: wrap; gap: 6px; }
    .review button.active[data-decision='accept'] { background: #dff3e4; border-color: #4b9a60; }
    .review button.active[data-decision='fix'] { background: #fff1c9; border-color: #c28b16; }
    .review button.active[data-decision='reject'] { background: #f9dddd; border-color: #bb5555; }
    .review input { box-sizing: border-box; width: 100%; margin-top: 8px; }
    .card[data-decision='accept'] { border-left: 5px solid #4b9a60; }
    .card[data-decision='fix'] { border-left: 5px solid #c28b16; }
    .card[data-decision='reject'] { border-left: 5px solid #bb5555; }
    .hidden { display: none !important; }
    @media (max-width: 760px) { .compare { grid-template-columns: 1fr; } }
    """
    cards = []
    for idx, row in enumerate(rows):
        metadata = json.loads(row["metadata"].read_text(encoding="utf-8"))
        if isinstance(metadata, dict):
            event_times = metadata.get("timestamps", [])
        elif metadata:
            event_times = metadata[0].get("timestamp", [])
        else:
            event_times = []
        event_start = float(event_times[0]) if len(event_times) >= 1 else 0.0
        event_end = float(event_times[1]) if len(event_times) >= 2 else event_start
        audio_id = f"vi-audio-{idx}"
        now_id = f"vi-now-{idx}"
        clean_block = ""
        if row["clean"] is not None:
            clean_block = f"<div class='label'>Clean input</div><audio controls preload='none' src='{html.escape(rel(row['clean'], out_root))}'></audio>"
        overlap_text = f"<p class='text'><b>Overlap:</b> {html.escape(row.get('overlap_text', ''))}</p>" if row.get("overlap_text") else ""
        english_key = (row["version"], row["task"])
        if english_key not in english_examples and row["task"] == "backchannel":
            english_key = ("v1.5", "user_backchannel")
        pool = english_examples.get(english_key, [])
        english = pool[idx % len(pool)] if pool else None
        if english:
            english_clean = ""
            if english.get("clean") is not None:
                english_clean = f"<div class='label'>English clean_input.wav</div><audio controls preload='none' src='{html.escape(rel(english['clean'], out_root))}'></audio>"
            english_block = (
                "<div class='pane'>"
                f"<div class='label'>{html.escape(english['label'])}</div>"
                "<div class='label'>English input.wav</div>"
                f"<audio controls preload='none' src='{html.escape(rel(english['input'], out_root))}'></audio>"
                f"{english_clean}"
                "<div class='label'>English metadata</div>"
                f"<pre>{html.escape(json.dumps(english['metadata_json'], ensure_ascii=False, indent=2))}</pre>"
                "</div>"
            )
        else:
            english_block = (
                "<div class='pane'>"
                "<div class='label'>English FDB reference</div>"
                "<div class='missing'>No matching English clean/mixed example is bundled locally for this v1.5 category.</div>"
                "</div>"
            )
        cards.append(
            f"<section class='card' data-key='{html.escape(row['version'] + '/' + row['task'] + '/' + row['id'])}' data-version='{html.escape(row['version'])}' data-task='{html.escape(row['task'])}' data-decision=''>"
            f"<div class='title'>{html.escape(row['version'])} / {html.escape(row['task'])} / {html.escape(row['id'])}</div>"
            f"<span class='badge'>{html.escape(row['expected_action'])}</span>"
            f"<p class='text'><b>Main:</b> {html.escape(row['text'])}</p>"
            f"{overlap_text}"
            "<div class='compare'><div class='pane'>"
            "<div class='label'>Benchmark input.wav</div>"
            f"<audio id='{audio_id}' controls preload='none' src='{html.escape(rel(row['input'], out_root))}'></audio>"
            "<div class='timebar'>"
            f"<span class='now'>now <b id='{now_id}'>0.000</b>s</span>"
            f"<span>event <b>{event_start:.3f}</b>s - <b>{event_end:.3f}</b>s</span>"
            f"<button type='button' data-jump='{audio_id}' data-time='{event_start:.3f}'>jump start</button>"
            f"<button type='button' data-jump='{audio_id}' data-time='{event_end:.3f}'>jump end</button>"
            "</div>"
            f"{clean_block}"
            "<div class='label'>Metadata / labels hidden from model</div>"
            f"<pre>{html.escape(json.dumps(metadata, ensure_ascii=False, indent=2))}</pre>"
            "</div>"
            f"{english_block}</div>"
            "<div class='review'><div class='label'>Review decision</div><div class='review-actions'>"
            "<button type='button' data-review='accept'>Accept</button>"
            "<button type='button' data-review='fix'>Needs fix</button>"
            "<button type='button' data-review='reject'>Reject</button>"
            "<button type='button' data-review=''>Clear</button>"
            "</div><input type='text' data-note placeholder='Optional note: pronunciation, timing, overlap, label…'></div>"
            "</section>"
        )
    doc = f"""<!doctype html>
<html lang="vi">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(page_title)}</title>
  <style>{style}</style>
</head>
<body>
  <h1>{html.escape(page_title)}</h1>
  <p class="note">Review these {len(rows)} benchmark samples. Decisions and notes are saved in this browser. Use <b>Export JSON</b> when finished so the review can be applied to the dataset.</p>
  <div class="toolbar">
    <select id="version-filter"><option value="">All versions</option><option>v1.0</option><option>v1.5</option></select>
    <select id="task-filter"><option value="">All tasks</option></select>
    <select id="status-filter"><option value="">All statuses</option><option value="unreviewed">Unreviewed</option><option value="accept">Accepted</option><option value="fix">Needs fix</option><option value="reject">Rejected</option></select>
    <button type="button" id="next-unreviewed">Next unreviewed</button>
    <button type="button" id="export-review">Export JSON</button>
    <span class="progress" id="progress"></span>
  </div>
  <div class="grid">{''.join(cards)}</div>
  <script>
    document.querySelectorAll("audio[id^='vi-audio-']").forEach((audio) => {{
      const idx = audio.id.replace("vi-audio-", "");
      const out = document.getElementById(`vi-now-${{idx}}`);
      audio.addEventListener("timeupdate", () => {{
        if (out) out.textContent = audio.currentTime.toFixed(3);
      }});
    }});
    document.querySelectorAll("button[data-jump]").forEach((btn) => {{
      btn.addEventListener("click", () => {{
        const audio = document.getElementById(btn.dataset.jump);
        if (!audio) return;
        audio.currentTime = Number(btn.dataset.time);
        audio.play();
      }});
    }});
    const storageKey = "fdb_vi_pilot_160_review_v3";
    let reviews = {{}};
    try {{ reviews = JSON.parse(localStorage.getItem(storageKey) || "{{}}"); }} catch (_) {{ reviews = {{}}; }}
    const cards = [...document.querySelectorAll(".card")];
    const taskFilter = document.getElementById("task-filter");
    [...new Set(cards.map(c => c.dataset.task))].sort().forEach(task => {{
      const option = document.createElement("option"); option.value = task; option.textContent = task; taskFilter.appendChild(option);
    }});
    function save() {{ localStorage.setItem(storageKey, JSON.stringify(reviews)); update(); }}
    function paint(card) {{
      const review = reviews[card.dataset.key] || {{}};
      card.dataset.decision = review.decision || "";
      card.querySelectorAll("[data-review]").forEach(b => b.classList.toggle("active", b.dataset.review === review.decision && !!review.decision));
      card.querySelector("[data-note]").value = review.note || "";
    }}
    function update() {{
      const version = document.getElementById("version-filter").value;
      const task = taskFilter.value;
      const status = document.getElementById("status-filter").value;
      cards.forEach(card => {{
        const decision = card.dataset.decision;
        const visible = (!version || card.dataset.version === version) && (!task || card.dataset.task === task) && (!status || (status === "unreviewed" ? !decision : decision === status));
        card.classList.toggle("hidden", !visible);
      }});
      const reviewed = cards.filter(c => c.dataset.decision).length;
      document.getElementById("progress").textContent = `${{reviewed}} / ${{cards.length}} reviewed`;
    }}
    cards.forEach(card => {{
      paint(card);
      card.querySelectorAll("[data-review]").forEach(button => button.addEventListener("click", () => {{
        const current = reviews[card.dataset.key] || {{}}; current.decision = button.dataset.review; current.note = card.querySelector("[data-note]").value.trim();
        if (!current.decision && !current.note) delete reviews[card.dataset.key]; else reviews[card.dataset.key] = current;
        paint(card); save();
      }}));
      card.querySelector("[data-note]").addEventListener("change", event => {{
        const current = reviews[card.dataset.key] || {{}}; current.note = event.target.value.trim();
        if (!current.decision && !current.note) delete reviews[card.dataset.key]; else reviews[card.dataset.key] = current;
        save();
      }});
    }});
    ["version-filter", "task-filter", "status-filter"].forEach(id => document.getElementById(id).addEventListener("change", update));
    document.getElementById("next-unreviewed").addEventListener("click", () => {{
      const card = cards.find(c => !c.dataset.decision); if (card) {{ card.classList.remove("hidden"); card.scrollIntoView({{behavior:"smooth", block:"start"}}); }}
    }});
    document.getElementById("export-review").addEventListener("click", () => {{
      const payload = {{dataset:"fdb_vi_pilot_160_20260710", exported_at:new Date().toISOString(), total:cards.length, reviews}};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{type:"application/json"}});
      const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `fdb_vi_review_${{new Date().toISOString().slice(0,10)}}.json`; link.click(); URL.revokeObjectURL(link.href);
    }});
    update();
  </script>
</body>
</html>
"""
    (out_root / filename).write_text(doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/fdb_vi_benchmark_preview")
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()

    out_root = Path(args.out_dir)
    if args.html_only:
        build_html(out_root, load_existing_rows(out_root))
        print(out_root / "index.html")
        return

    if out_root.exists() and args.overwrite:
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    from vieneu import Vieneu

    tts = Vieneu(mode="v3turbo", backend="pytorch")
    rows = make_v1_0(tts, out_root, args.temperature)
    rows.extend(make_v1_5(tts, out_root, args.temperature))

    manifest = []
    for row in rows:
        manifest.append(
            {
                "version": row["version"],
                "task": row["task"],
                "id": row["id"],
                "input": rel(row["input"], out_root),
                "clean_input": rel(row["clean"], out_root) if row["clean"] is not None else None,
                "metadata": rel(row["metadata"], out_root),
                "expected_action": row["expected_action"],
            }
        )
    (out_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    build_html(out_root, rows)
    print(out_root / "index.html")


if __name__ == "__main__":
    main()
