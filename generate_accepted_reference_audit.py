from __future__ import annotations

from pathlib import Path
import argparse
import html
import json

import soundfile as sf
from huggingface_hub import hf_hub_download
from vieneu import Vieneu


PROMPTS = [
    {
        "id": "hanoi_route",
        "label": "Northern place names",
        "text": "Bạn ra Hà Nội bao giờ chưa? Mình muốn đặt xe từ Hồ Gươm về Cầu Giấy chiều nay.",
    },
    {
        "id": "northern_polite",
        "label": "Northern polite",
        "text": "Dạ vâng, đúng rồi ạ. Mình nhờ bạn kiểm tra giúp lịch hẹn lúc ba giờ chiều nhé.",
    },
    {
        "id": "correction",
        "label": "Correction",
        "text": "Không phải thế, mình bảo là chiều nay cơ. À, chính xác là sau bốn giờ mới được.",
    },
    {
        "id": "hesitation",
        "label": "Hesitation",
        "text": "Ờ thì mình đang nghĩ là... ừm... để lát nữa nói tiếp cũng được.",
    },
    {
        "id": "interruption",
        "label": "Interruption",
        "text": "Khoan đã, mình đổi ý rồi. Đừng tìm khách sạn ở Nha Trang nữa, tìm giúp mình ở Đà Lạt đi.",
    },
    {
        "id": "backchannel",
        "label": "Backchannel",
        "text": "Vâng, đúng rồi ạ.",
    },
    {
        "id": "daily_casual",
        "label": "Daily casual",
        "text": "Mình muốn mua ít đồ ăn tối, nhưng mà trời đang mưa nên chắc đặt giao hàng cho tiện.",
    },
]


def parse_assessment(assessment: dict) -> dict:
    grouped = {}
    for key, value in assessment.items():
        ref_id, field = key.split("::", 1)
        grouped.setdefault(ref_id, {})[field] = value
    return grouped


def trim_wav(src: Path, dst: Path, seconds: float) -> None:
    audio, sr = sf.read(src)
    sf.write(dst, audio[: int(sr * seconds)], sr)


def build_html(out_dir: Path, manifest: dict) -> None:
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f7f7f4; color: #202428; }
    h1 { margin: 0 0 8px; }
    .note { max-width: 1000px; color: #5d666e; line-height: 1.45; }
    .toolbar { display: flex; gap: 8px; margin: 16px 0; align-items: center; flex-wrap: wrap; }
    button { border: 1px solid #bfc5c9; background: #fff; border-radius: 6px; padding: 6px 9px; cursor: pointer; font-weight: 600; }
    button:hover { background: #eef4ff; }
    .export { background: #1f6feb; border-color: #1f6feb; color: white; }
    textarea { width: min(1000px, 100%); min-height: 200px; display: none; margin: 12px 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    table { border-collapse: collapse; width: max-content; min-width: 1500px; background: white; }
    .wrap { overflow-x: auto; border: 1px solid #ddd; }
    th, td { border: 1px solid #ddd; padding: 10px; vertical-align: top; }
    th { background: #efefe8; text-align: left; position: sticky; top: 0; z-index: 2; }
    th.ref, td.ref { position: sticky; left: 0; z-index: 1; background: #fbfbf8; min-width: 310px; max-width: 360px; }
    th.ref { z-index: 3; }
    td.clip { min-width: 230px; max-width: 250px; }
    audio { width: 215px; display: block; }
    .label { font-weight: 700; margin-bottom: 6px; }
    .small { color: #687078; font-size: 12px; line-height: 1.35; word-break: break-word; }
    .tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 10px; }
    .tag.active { background: #165dff; color: white; border-color: #165dff; }
    .tag[data-tag="bad"].active { background: #b42318; border-color: #b42318; }
    .status { color: #687078; font-size: 13px; }
    """
    by_key = {(item["reference_id"], item["prompt_id"]): item for item in manifest["items"]}
    header = ["<th class='ref'>Accepted reference</th>"]
    for prompt in manifest["prompts"]:
        header.append(
            f"<th>{html.escape(prompt['label'])}<p class='small'>{html.escape(prompt['text'])}</p></th>"
        )
    rows = []
    for ref in manifest["references"]:
        cells = [
            "<td class='ref'>"
            f"<div class='label'>{html.escape(ref['id'])}</div>"
            f"<audio controls preload='none' src='{html.escape(ref['file'])}'></audio>"
            f"<p class='small'>Expected dialect: {html.escape(ref['dialect'])}; quality: {html.escape(ref['quality'])}<br>{html.escape(ref['source'])}</p>"
            "</td>"
        ]
        for prompt in manifest["prompts"]:
            item = by_key[(ref["id"], prompt["id"])]
            key = f"{ref['id']}::{prompt['id']}"
            tags = "".join(
                f"<button class='tag' data-key='{html.escape(key)}' data-tag='{tag}'>{tag}</button>"
                for tag in ["N", "S", "C", "mixed", "bad"]
            )
            cells.append(
                "<td class='clip'>"
                f"<audio controls preload='none' src='{html.escape(item['file'])}'></audio>"
                f"<div class='tags'>{tags}</div>"
                "</td>"
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    script = """
    const STORAGE_KEY = "fdb_vi_accepted_ref_audit_tags";
    function loadTags(){try{return JSON.parse(localStorage.getItem(STORAGE_KEY)||"{}")}catch{return {}}}
    function saveTags(tags){localStorage.setItem(STORAGE_KEY, JSON.stringify(tags)); updateStatus(tags)}
    function paint(tags){document.querySelectorAll(".tag").forEach(btn=>btn.classList.toggle("active", tags[btn.dataset.key]===btn.dataset.tag))}
    function updateStatus(tags){const total=new Set(Array.from(document.querySelectorAll(".tag")).map(b=>b.dataset.key)).size; document.getElementById("status").textContent=`${Object.keys(tags).length}/${total} clips tagged`}
    document.addEventListener("click", ev=>{const btn=ev.target.closest(".tag"); if(!btn)return; const tags=loadTags(); if(tags[btn.dataset.key]===btn.dataset.tag) delete tags[btn.dataset.key]; else tags[btn.dataset.key]=btn.dataset.tag; saveTags(tags); paint(tags)})
    document.getElementById("export").addEventListener("click",()=>{const out=document.getElementById("exportText"); out.style.display="block"; out.value=JSON.stringify(loadTags(), null, 2); out.select()})
    document.getElementById("clear").addEventListener("click",()=>{if(!confirm("Clear all local tags?"))return; localStorage.removeItem(STORAGE_KEY); paint({}); updateStatus({}); document.getElementById("exportText").style.display="none"})
    const tags=loadTags(); paint(tags); updateStatus(tags)
    """
    doc = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Accepted Reference Dialect Audit</title><style>{style}</style></head>
<body><h1>Accepted Reference Dialect Audit</h1>
<p class="note">These refs were marked clean/accepted. Listen row-wise and tag whether zero-shot outputs preserve expected dialect. Tags are saved locally; export JSON when done.</p>
<div class="toolbar"><button id="export" class="export">Export JSON</button><button id="clear">Clear tags</button><span id="status" class="status"></span></div>
<textarea id="exportText" readonly></textarea>
<div class="wrap"><table><thead><tr>{''.join(header)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<script>{script}</script></body></html>"""
    (out_dir / "index.html").write_text(doc, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening-manifest", default="outputs/fdb_vi_reference_screening/manifest.json")
    parser.add_argument("--assessment", default="outputs/fdb_vi_reference_screening/assessment.json")
    parser.add_argument("--out-dir", default="outputs/fdb_vi_accepted_reference_audit")
    parser.add_argument("--trim-seconds", type=float, default=6.0)
    args = parser.parse_args()

    screening = json.loads(Path(args.screening_manifest).read_text(encoding="utf-8"))
    assessment = parse_assessment(json.loads(Path(args.assessment).read_text(encoding="utf-8")))
    ref_by_id = {ref["id"]: ref for ref in screening["references"]}
    accepted_ids = [
        ref_id for ref_id, fields in assessment.items()
        if fields.get("decision") == "accept" and fields.get("quality") == "clean"
    ]

    out_dir = Path(args.out_dir)
    ref_dir = out_dir / "refs"
    audio_dir = out_dir / "audio"
    ref_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    print(f"Accepted clean references: {len(accepted_ids)}")
    tts = Vieneu(mode="v3turbo", backend="pytorch")
    manifest = {"references": [], "prompts": PROMPTS, "items": []}

    for ref_id in accepted_ids:
        ref = ref_by_id[ref_id]
        fields = assessment[ref_id]
        src = Path(hf_hub_download("thanhnew2001/VietSuperSpeech", filename=ref["dataset_audio"], repo_type="dataset"))
        ref_file = ref_dir / f"{ref_id}.wav"
        trim_wav(src, ref_file, args.trim_seconds)
        manifest["references"].append(
            {
                "id": ref_id,
                "file": str(ref_file.relative_to(out_dir)),
                "source": ref["source"],
                "dialect": fields["dialect"],
                "quality": fields["quality"],
            }
        )
        for prompt in PROMPTS:
            out_file = audio_dir / f"{ref_id}__{prompt['id']}.wav"
            print(f"{ref_id} -> {prompt['id']}")
            audio = tts.infer(prompt["text"], ref_audio=str(ref_file), temperature=0.8)
            tts.save(audio, str(out_file))
            manifest["items"].append(
                {
                    "reference_id": ref_id,
                    "prompt_id": prompt["id"],
                    "file": str(out_file.relative_to(out_dir)),
                }
            )

    with (out_dir / "manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    build_html(out_dir, manifest)
    print(out_dir / "index.html")


if __name__ == "__main__":
    main()
