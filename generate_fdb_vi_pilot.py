from __future__ import annotations

from pathlib import Path
import argparse
import json
import random
import shutil

from generate_fdb_vi_benchmark_preview import (
    SPEAKERS,
    build_html,
    mix_at,
    read_audio,
    silence,
    synth,
    write_audio,
)


SCENARIOS = [
    # Reception and service assistants (5/20).
    {"slug": "hotel_robot", "family": "service_assistant", "interaction": "human_machine", "setting": "sảnh khách sạn", "action": "đặt phòng", "detail": "giờ nhận phòng", "request": "Bạn kiểm tra giúp mình phòng đôi yên tĩnh cho tối mai được không?", "redirect": "À khoan, mình cần phòng gia đình cho tối thứ bảy nhé."},
    {"slug": "clinic_kiosk", "family": "service_assistant", "interaction": "human_machine", "setting": "phòng khám", "action": "đổi lịch khám", "detail": "khám tổng quát", "request": "Bạn xem giúp mình còn lịch khám tổng quát nào vào chiều nay không?", "redirect": "Mình đổi ý rồi, bạn tìm lịch vào sáng mai giúp mình nhé."},
    {"slug": "airport_assistant", "family": "service_assistant", "interaction": "human_machine", "setting": "sân bay", "action": "đổi chuyến bay", "detail": "quầy làm thủ tục", "request": "Bạn chỉ giúp mình quầy làm thủ tục cho chuyến bay đi Đà Nẵng nhé.", "redirect": "À không, bạn kiểm tra giúp mình thủ tục đổi sang chuyến muộn hơn."},
    {"slug": "bank_assistant", "family": "service_assistant", "interaction": "human_machine", "setting": "ngân hàng", "action": "mở tài khoản", "detail": "xác minh giấy tờ", "request": "Bạn hướng dẫn giúp mình cần giấy tờ gì để mở tài khoản nhé.", "redirect": "Khoan, trước tiên bạn chỉ mình cách đổi số điện thoại đã đăng ký."},
    {"slug": "apartment_robot", "family": "service_assistant", "interaction": "human_machine", "setting": "sảnh chung cư", "action": "đăng ký khách", "detail": "thẻ ra vào", "request": "Bạn đăng ký giúp mình một khách tới thăm vào tối nay được không?", "redirect": "À, đổi lại thành hai khách và họ sẽ đến vào sáng mai nhé."},
    # Smart-home assistants (5/20).
    {"slug": "home_lighting", "family": "smart_home", "interaction": "human_machine", "setting": "phòng khách", "action": "điều chỉnh đèn", "detail": "chế độ đọc sách", "request": "Bạn giảm đèn phòng khách xuống còn ba mươi phần trăm nhé.", "redirect": "Khoan, đừng giảm nữa, chuyển sang chế độ đọc sách giúp mình."},
    {"slug": "home_climate", "family": "smart_home", "interaction": "human_machine", "setting": "phòng ngủ", "action": "điều chỉnh điều hòa", "detail": "nhiệt độ ban đêm", "request": "Bạn đặt điều hòa phòng ngủ ở hai mươi sáu độ đến sáu giờ sáng nhé.", "redirect": "À khoan, đặt hai mươi bảy độ và tắt lúc năm giờ rưỡi."},
    {"slug": "home_security", "family": "smart_home", "interaction": "human_machine", "setting": "căn hộ", "action": "kiểm tra an ninh", "detail": "cửa ban công", "request": "Bạn kiểm tra giúp mình cửa chính và cửa ban công đã khóa chưa.", "redirect": "Khoan, chỉ khóa cửa chính thôi, cửa ban công để mở nhé."},
    {"slug": "home_cooking", "family": "smart_home", "interaction": "human_machine", "setting": "nhà bếp", "action": "đặt hẹn giờ", "detail": "lò nướng", "request": "Bạn đặt hẹn giờ lò nướng trong hai mươi phút giúp mình.", "redirect": "Mình nói nhầm, đặt mười lăm phút thôi và nhắc mình trước hai phút."},
    {"slug": "home_media", "family": "smart_home", "interaction": "human_machine", "setting": "phòng làm việc", "action": "phát nhạc", "detail": "âm lượng loa", "request": "Bạn phát danh sách nhạc tập trung với âm lượng nhỏ nhé.", "redirect": "À thôi, chuyển sang tiếng mưa và hẹn tắt sau một giờ."},
    # In-car assistants (5/20).
    {"slug": "car_navigation", "family": "in_car", "interaction": "human_machine", "setting": "trong ô tô", "action": "tìm đường", "detail": "tuyến đường ít kẹt xe", "request": "Bạn tìm đường ít kẹt xe nhất tới sân bay giúp mình nhé.", "redirect": "Khoan, mình cần ghé trạm xăng trước rồi mới tới sân bay."},
    {"slug": "car_charging", "family": "in_car", "interaction": "human_machine", "setting": "trên đường cao tốc", "action": "tìm trạm sạc", "detail": "mức pin còn lại", "request": "Bạn tìm trạm sạc nhanh gần nhất trên tuyến đường này nhé.", "redirect": "À, ưu tiên trạm có quán cà phê và còn cổng sạc trống."},
    {"slug": "car_climate", "family": "in_car", "interaction": "human_machine", "setting": "trong ô tô", "action": "điều chỉnh nhiệt độ", "detail": "ghế hành khách", "request": "Bạn giảm nhiệt độ bên ghế hành khách xuống một chút nhé.", "redirect": "Khoan, giữ nguyên nhiệt độ và bật sưởi ghế mức thấp thôi."},
    {"slug": "car_call", "family": "in_car", "interaction": "human_machine", "setting": "trong ô tô", "action": "gọi điện rảnh tay", "detail": "cuộc gọi công việc", "request": "Bạn gọi cho chị Lan trong danh bạ công việc giúp mình.", "redirect": "À khoan, nhắn chị ấy là mình sẽ gọi lại sau mười phút."},
    {"slug": "car_parking", "family": "in_car", "interaction": "human_machine", "setting": "gần trung tâm thành phố", "action": "tìm chỗ đỗ xe", "detail": "bãi đỗ có mái che", "request": "Bạn tìm giúp mình bãi đỗ xe còn chỗ gần đây nhé.", "redirect": "Mình đổi ý rồi, tìm bãi có mái che dù xa hơn một chút."},
    # Human-to-human source conversations (5/20).
    {"slug": "coworker_planning", "family": "human_human", "interaction": "human_human", "setting": "văn phòng", "action": "sắp lịch họp", "detail": "phòng họp", "request": "Bạn xem giúp mình chiều mai nhóm mình họp lúc nào thì tiện nhất?", "redirect": "Khoan, chiều mai mình bận rồi, chuyển sang sáng thứ sáu nhé."},
    {"slug": "family_errand", "family": "human_human", "interaction": "human_human", "setting": "ở nhà", "action": "lên danh sách mua đồ", "detail": "bữa tối gia đình", "request": "Bạn nhắc mình tối nay cần mua những gì cho bữa cơm nhé.", "redirect": "À, tối nay có thêm hai người, mình mua đồ cho sáu người nhé."},
    {"slug": "friends_trip", "family": "human_human", "interaction": "human_human", "setting": "quán cà phê", "action": "lên lịch đi chơi", "detail": "chuyến đi cuối tuần", "request": "Bạn nghĩ cuối tuần này tụi mình nên đi biển hay lên núi?", "redirect": "Khoan, dự báo có mưa rồi, mình tìm chỗ nào gần thành phố thôi."},
    {"slug": "driver_passenger", "family": "human_human", "interaction": "human_human", "setting": "trên xe", "action": "thống nhất điểm đón", "detail": "lộ trình", "request": "Anh cho em xuống ở cổng phía đông của trung tâm thương mại nhé.", "redirect": "À anh ơi, đổi sang cổng phía nam giúp em, bạn em đang chờ ở đó."},
    {"slug": "student_teacher", "family": "human_human", "interaction": "human_human", "setting": "lớp học", "action": "hỏi về bài tập", "detail": "hạn nộp bài", "request": "Thầy giải thích giúp em yêu cầu của phần cuối bài tập được không ạ?", "redirect": "À, trước đó thầy cho em hỏi lại cách làm câu số ba được không ạ?"},
]

SPEAKER_CYCLE = ["north_female", "north_male", "south_female", "south_male"]


def sample_id(i: int) -> str:
    return f"{i + 1:06d}"


def speaker_for(i: int, offset: int = 0) -> str:
    return SPEAKER_CYCLE[(i + offset) % len(SPEAKER_CYCLE)]


def scenario_for(i: int) -> dict:
    return SCENARIOS[i % len(SCENARIOS)]


def split_request_for_pause(text: str) -> list[str]:
    words = text.rstrip(".?!").split()
    cut = min(len(words) - 2, max(4, round(len(words) * 0.6)))
    return [" ".join(words[:cut]), " ".join(words[cut:]) + text[-1]]


def v1_pause_spec(i: int) -> dict:
    scenario = scenario_for(i)
    return {
        "id": sample_id(i),
        "task": "pause_handling",
        "speaker": speaker_for(i),
        "parts": split_request_for_pause(scenario["request"]),
        "pause_sec": [0.7, 0.85, 1.0, 1.15][i % 4], "scenario": scenario,
    }


def v1_smooth_spec(i: int) -> dict:
    scenario = scenario_for(i)
    return {"id": sample_id(i), "task": "smooth_turn_taking", "speaker": speaker_for(i), "text": scenario["request"], "scenario": scenario}


def v1_interruption_spec(i: int) -> dict:
    scenario = scenario_for(i)
    return {
        "id": sample_id(i),
        "task": "user_interruption",
        "speaker": speaker_for(i),
        "context_text": scenario["request"],
        "interrupt_text": scenario["redirect"],
        "wait_sec": [2.5, 3.0, 3.5][i % 3],
        "scenario": scenario,
    }


def v1_backchannel_spec(i: int) -> dict:
    scenario = scenario_for(i)
    place, action, detail = scenario["setting"], scenario["action"], scenario["detail"]
    prompts = [
        f"Bạn giải thích kỹ giúp mình quy trình {action} ở {place} nhé.",
        f"Bạn trình bày chi tiết những điều cần lưu ý về {detail} được không?",
        f"Bạn hướng dẫn từng bước để mình chuẩn bị cho việc {action} nhé.",
        f"Bạn phân tích các lựa chọn liên quan đến {detail} giúp mình được không?",
    ]
    backchannels = ["Vâng, bạn nói tiếp đi.", "Dạ, mình đang nghe.", "Ừm, đúng rồi.", "À, mình hiểu rồi."]
    return {
        "id": sample_id(i), "task": "backchannel", "speaker": speaker_for(i),
        "context_text": prompts[i % len(prompts)], "backchannel_text": backchannels[(i // 2) % len(backchannels)],
        "wait_sec": [3.0, 3.5, 4.0][i % 3],
        "scenario": scenario,
    }


def v1_5_spec(task: str, i: int) -> dict:
    scenario = scenario_for(i)
    place, action, detail = scenario["setting"], scenario["action"], scenario["detail"]
    main_speaker = speaker_for(i)
    overlap_speaker = main_speaker if task in {"user_interruption", "user_backchannel", "talking_to_other"} else speaker_for(i, 1)
    base = {
        "id": sample_id(i),
        "task": task,
        "main_speaker": main_speaker,
        "overlap_speaker": overlap_speaker,
        "context_text": f"Bối cảnh {scenario['interaction']}: {scenario['family']} tại {place}.",
        "current_turn_text": scenario["request"],
        "scenario_context": scenario,
    }
    if task == "user_interruption":
        base.update(
            {
                "overlap_text": scenario["redirect"],
                "insert_ratio": 1.0,
                "gain": 1.0,
                "expected_action": "<|S-L|>",
            }
        )
    elif task == "user_backchannel":
        base.update(
            {
                "overlap_text": ["Vâng, đúng rồi ạ.", "Dạ, mình hiểu rồi.", "Ừm, đúng thế."][i % 3],
                "insert_ratio": [0.38, 0.48, 0.58][i % 3],
                "gain": 0.8,
                "expected_action": "<|C-S|>",
            }
        )
    elif task == "talking_to_other":
        side_speech = {
            "service_assistant": ["Anh giữ giúp em cái túi một lát nhé.", "Chị đứng chờ em cạnh cửa giúp em nhé."],
            "smart_home": ["Con lấy giúp mẹ cốc nước trong bếp nhé.", "Anh đóng giúp em cửa sổ bên kia với."],
            "in_car": ["Em cầm giúp anh chai nước ở ghế sau nhé.", "Con ngồi yên và cài dây an toàn vào nhé."],
            "human_human": ["Chị chờ em trả lời tin nhắn này một lát nhé.", "Anh nhắc mọi người đợi em năm phút nhé."],
        }[scenario["family"]]
        base.update(
            {
                "overlap_text": side_speech[i % len(side_speech)],
                "insert_ratio": [0.35, 0.5, 0.62][i % 3],
                "gain": 0.72,
                "expected_action": "<|C-S|>",
            }
        )
    else:
        background = {
            "service_assistant": ["Mời khách số hai mươi ba tới quầy hướng dẫn.", "Quầy dịch vụ bên phải sẽ đóng cửa trong mười phút nữa."],
            "smart_home": ["Ngoài hành lang có người đang chuyển đồ lên tầng trên.", "Nhà bên cạnh đang sửa chữa nên có thể hơi ồn."],
            "in_car": ["Bản tin giao thông: đoạn đường phía trước đang ùn tắc.", "Thông báo trên radio: trời có thể mưa lớn vào cuối giờ chiều."],
            "human_human": ["Mọi người nhớ nộp tài liệu trước cuối giờ chiều nhé.", "Bàn phía trong vừa có khách đặt chỗ trước rồi."],
        }[scenario["family"]]
        base.update(
            {
                "overlap_text": background[i % len(background)],
                "insert_ratio": [0.3, 0.45, 0.6][i % 3],
                "gain": 0.35,
                "expected_action": "<|C-S|>",
            }
        )
    return base


def maybe_skip(task_index: int, num_shards: int, shard_index: int) -> bool:
    return task_index % num_shards != shard_index


def distant_speech(audio, strength: float = 0.7):
    """Make a secondary utterance sound off-mic instead of like a foreground speaker."""
    import numpy as np

    kernel_size = max(3, int(5 + strength * 18))
    kernel = np.ones(kernel_size, dtype=np.float32) / kernel_size
    muffled = np.convolve(audio, kernel, mode="same")
    delay = int(900 + strength * 1100)
    out = muffled.copy()
    if len(out) > delay:
        out[delay:] += muffled[:-delay] * (0.12 + 0.12 * strength)
    return out * (0.52 - 0.22 * strength)


def make_v1_0_sample(tts, out_root: Path, spec: dict, temperature: float) -> dict:
    import numpy as np

    sample_dir = out_root / "v1_0" / spec["task"] / spec["id"]
    stream_dir = sample_dir / "source_streams"
    ref = Path(SPEAKERS[spec["speaker"]])
    sample_dir.mkdir(parents=True, exist_ok=True)

    if spec["task"] == "pause_handling":
        p1 = synth(tts, spec["parts"][0], ref, stream_dir / "part_1.wav", temperature)
        p2 = synth(tts, spec["parts"][1], ref, stream_dir / "part_2.wav", temperature)
        a1, sr = read_audio(p1)
        a2, sr2 = read_audio(p2)
        if sr != sr2:
            raise ValueError("Mismatched sample rates")
        start = len(a1) / sr
        end = start + float(spec["pause_sec"])
        final = np.concatenate([a1, silence(spec["pause_sec"], sr), a2, silence(0.5, sr)])
        write_audio(sample_dir / "input.wav", final, sr)
        legacy = [{"text": "[PAUSE]", "timestamp": [round(start, 3), round(end, 3)]}]
        (sample_dir / "pause.json").write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        text = f"{spec['parts'][0]} ... {spec['parts'][1]}"
        primary_text, event_type, event_text = text, "pause", "[PAUSE]"
        expected = "<|C-L|>"
    elif spec["task"] == "smooth_turn_taking":
        main = synth(tts, spec["text"], ref, stream_dir / "main.wav", temperature)
        audio, sr = read_audio(main)
        start = len(audio) / sr
        write_audio(sample_dir / "input.wav", np.concatenate([audio, silence(5.0, sr)]), sr)
        end = start + 0.4
        legacy = [{"text": "[TURN-TAKING]", "timestamp": [round(start, 3), round(end, 3)]}]
        (sample_dir / "turn_taking.json").write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        text = spec["text"]
        primary_text, event_type, event_text = text, "turn_end", "[TURN_END]"
        expected = "<|S-S|>"
    elif spec["task"] == "user_interruption":
        context = synth(tts, spec["context_text"], ref, stream_dir / "context.wav", temperature)
        interrupt = synth(tts, spec["interrupt_text"], ref, stream_dir / "interrupt.wav", temperature)
        c, sr = read_audio(context)
        intr, sr2 = read_audio(interrupt)
        if sr != sr2:
            raise ValueError("Mismatched sample rates")
        start = len(c) / sr + float(spec["wait_sec"])
        end = start + len(intr) / sr
        write_audio(sample_dir / "context.wav", c, sr)
        write_audio(sample_dir / "interrupt.wav", intr, sr)
        write_audio(sample_dir / "input.wav", np.concatenate([c, silence(spec["wait_sec"], sr), intr, silence(0.6, sr)]), sr)
        legacy = [{"context": spec["context_text"], "interrupt": spec["interrupt_text"], "timestamp": [round(start, 3), round(end, 3)]}]
        (sample_dir / "interrupt.json").write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
        text = f"{spec['context_text']} ... {spec['interrupt_text']}"
        primary_text, event_type, event_text = spec["context_text"], "user_interruption", spec["interrupt_text"]
        expected = "<|S-L|>"
    else:
        main = synth(tts, spec["context_text"], ref, stream_dir / "context.wav", temperature)
        cue = synth(tts, spec["backchannel_text"], ref, stream_dir / "backchannel.wav", temperature)
        audio, sr = read_audio(main)
        cue_audio, sr2 = read_audio(cue)
        if sr != sr2:
            raise ValueError("Mismatched sample rates")
        start = len(audio) / sr + float(spec["wait_sec"])
        end = start + len(cue_audio) / sr
        write_audio(sample_dir / "input.wav", np.concatenate([audio, silence(spec["wait_sec"], sr), cue_audio, silence(5.0, sr)]), sr)
        text = f"{spec['context_text']} ... {spec['backchannel_text']}"
        primary_text, event_type, event_text = spec["context_text"], "backchannel", spec["backchannel_text"]
        expected = "<|C-L|>"

    scenario = spec["scenario"]
    meta = {
        "dataset": "Vietnamese-FDB",
        "dataset_version": "1.0",
        "schema_version": "1",
        "sample_id": spec["id"],
        "task": spec["task"],
        "primary_text": primary_text,
        "event_type": event_type,
        "event_text": event_text,
        "timestamps": [round(start, 3), round(end, 3)],
        "expected_action": expected,
        "primary_speaker": spec["speaker"],
        "event_speaker": spec["speaker"],
        "context_family": scenario["family"],
        "interaction_type": scenario["interaction"],
        "setting": scenario["setting"],
        "scenario_id": scenario["slug"],
        "source_methodology": "English-FDB-v1.0",
    }
    meta_path = sample_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "version": "v1.0",
        "task": spec["task"],
        "id": spec["id"],
        "input": sample_dir / "input.wav",
        "clean": None,
        "metadata": meta_path,
        "text": text,
        "expected_action": expected,
    }


def make_v1_5_sample(tts, out_root: Path, spec: dict, temperature: float) -> dict:
    import numpy as np

    sample_dir = out_root / "v1_5" / spec["task"] / spec["id"]
    stream_dir = sample_dir / "source_streams"
    main_ref = Path(SPEAKERS[spec["main_speaker"]])
    overlap_ref = Path(SPEAKERS[spec["overlap_speaker"]])
    sample_dir.mkdir(parents=True, exist_ok=True)

    main = synth(tts, spec["current_turn_text"], main_ref, stream_dir / "main_user.wav", temperature)
    overlap = synth(tts, spec["overlap_text"], overlap_ref, stream_dir / "overlap.wav", temperature)
    main_audio, sr = read_audio(main)
    overlap_audio, sr2 = read_audio(overlap)
    if sr != sr2:
        raise ValueError("Mismatched sample rates")

    main_duration = len(main_audio) / sr
    overlap_duration = len(overlap_audio) / sr
    if spec["task"] == "user_interruption":
        wait_sec = [2.5, 3.0, 3.5][(int(spec["id"]) - 1) % 3]
        insert_at = main_duration + wait_sec
        clean = np.concatenate([main_audio, silence(wait_sec + overlap_duration + 5.0, sr)])
        mixed = np.concatenate([main_audio, silence(wait_sec, sr), overlap_audio, silence(5.0, sr)])
    else:
        wait_sec = [3.0, 3.5, 4.0][(int(spec["id"]) - 1) % 3]
        insert_at = main_duration + wait_sec
        if spec["task"] == "talking_to_other":
            overlap_audio = distant_speech(overlap_audio, 0.45)
        elif spec["task"] == "background_speech":
            overlap_audio = distant_speech(overlap_audio, 0.9)
        clean = np.concatenate([main_audio, silence(wait_sec + overlap_duration + 5.0, sr)])
        mixed = np.concatenate([main_audio, silence(wait_sec, sr), overlap_audio, silence(5.0, sr)])

    write_audio(sample_dir / "clean_input.wav", clean, sr)
    write_audio(sample_dir / "input.wav", mixed, sr)
    scenario = spec["scenario_context"]
    meta = {
        "dataset": "Vietnamese-FDB",
        "dataset_version": "1.0",
        "schema_version": "1",
        "sample_id": spec["id"],
        "task": spec["task"],
        "primary_text": spec["current_turn_text"],
        "event_type": spec["task"],
        "event_text": spec["overlap_text"],
        "timestamps": [round(insert_at, 3), round(insert_at + overlap_duration, 3)],
        "expected_action": spec["expected_action"],
        "primary_speaker": spec["main_speaker"],
        "event_speaker": spec["overlap_speaker"],
        "context_family": scenario["family"],
        "interaction_type": scenario["interaction"],
        "setting": scenario["setting"],
        "scenario_id": scenario["slug"],
        "source_methodology": "English-FDB-v1.5",
    }
    meta_path = sample_dir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "version": "v1.5",
        "task": spec["task"],
        "id": spec["id"],
        "input": sample_dir / "input.wav",
        "clean": sample_dir / "clean_input.wav",
        "metadata": meta_path,
        "text": spec["current_turn_text"],
        "overlap_text": spec["overlap_text"],
        "expected_action": spec["expected_action"],
    }


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def write_manifest(out_root: Path, rows: list[dict]) -> None:
    manifest = [
        {
            "version": row["version"],
            "task": row["task"],
            "id": row["id"],
            "input": rel(row["input"], out_root),
            "clean_input": rel(row["clean"], out_root) if row.get("clean") is not None else None,
            "metadata": rel(row["metadata"], out_root),
            "expected_action": row["expected_action"],
        }
        for row in rows
    ]
    (out_root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def load_rows_from_manifest(out_root: Path) -> list[dict]:
    rows = []
    for item in json.loads((out_root / "manifest.json").read_text(encoding="utf-8")):
        meta_path = out_root / item["metadata"]
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(meta, dict):
            text = meta.get("primary_text") or meta.get("current_turn_text") or meta.get("context_text", "")
            overlap_text = meta.get("event_text") or meta.get("overlap_text") or meta.get("backchannel_text", "")
        elif meta and "context" in meta[0]:
            text = f"{meta[0]['context']} ... {meta[0]['interrupt']}"
            overlap_text = meta[0]["interrupt"]
        elif meta:
            text = meta[0].get("text", "")
            overlap_text = ""
        else:
            text = ""
            overlap_text = ""
        rows.append(
            {
                "version": item["version"],
                "task": item["task"],
                "id": item["id"],
                "input": out_root / item["input"],
                "clean": out_root / item["clean_input"] if item.get("clean_input") else None,
                "metadata": meta_path,
                "text": text,
                "overlap_text": overlap_text,
                "expected_action": item["expected_action"],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/fdb_vi_pilot_160")
    parser.add_argument("--samples-per-task", type=int, default=20)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--html-only", action="store_true")
    args = parser.parse_args()

    out_root = Path(args.out_dir)
    if args.html_only:
        build_html(out_root, load_rows_from_manifest(out_root))
        print(out_root / "index.html")
        return

    if args.overwrite and out_root.exists() and args.shard_index == 0:
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    random.seed(7)

    from vieneu import Vieneu

    tts = Vieneu(mode="v3turbo", backend="pytorch")
    rows = []
    tasks_v1 = [
        ("pause_handling", v1_pause_spec),
        ("smooth_turn_taking", v1_smooth_spec),
        ("backchannel", v1_backchannel_spec),
        ("user_interruption", v1_interruption_spec),
    ]
    tasks_v15 = ["user_interruption", "user_backchannel", "talking_to_other", "background_speech"]

    global_idx = 0
    for _, maker in tasks_v1:
        for i in range(args.samples_per_task):
            if not maybe_skip(global_idx, args.num_shards, args.shard_index):
                spec = maker(i)
                print(f"{spec['task']} {spec['id']}")
                rows.append(make_v1_0_sample(tts, out_root, spec, args.temperature))
            global_idx += 1

    for task in tasks_v15:
        for i in range(args.samples_per_task):
            if not maybe_skip(global_idx, args.num_shards, args.shard_index):
                spec = v1_5_spec(task, i)
                print(f"{spec['task']} {spec['id']}")
                rows.append(make_v1_5_sample(tts, out_root, spec, args.temperature))
            global_idx += 1

    shard_manifest = out_root / f"manifest_shard_{args.shard_index}.json"
    shard_manifest.write_text(
        json.dumps(
            [
                {
                    "version": row["version"],
                    "task": row["task"],
                    "id": row["id"],
                    "input": rel(row["input"], out_root),
                    "clean_input": rel(row["clean"], out_root) if row.get("clean") is not None else None,
                    "metadata": rel(row["metadata"], out_root),
                    "expected_action": row["expected_action"],
                }
                for row in rows
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    if args.num_shards == 1:
        write_manifest(out_root, rows)
        build_html(out_root, rows)
        print(out_root / "index.html")
    else:
        print(shard_manifest)


if __name__ == "__main__":
    main()
