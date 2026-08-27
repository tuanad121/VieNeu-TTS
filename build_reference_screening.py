from __future__ import annotations

from pathlib import Path
import argparse
import html
import json


def build_html(manifest: dict) -> str:
    style = """
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; background: #f7f7f4; color: #202428; }
    h1 { margin: 0 0 8px; }
    .note { max-width: 1000px; color: #5d666e; line-height: 1.45; }
    .toolbar { display: flex; gap: 8px; margin: 16px 0; align-items: center; flex-wrap: wrap; }
    button { border: 1px solid #bfc5c9; background: #fff; border-radius: 6px; padding: 6px 9px; cursor: pointer; font-weight: 600; }
    button:hover { background: #eef4ff; }
    .export { background: #1f6feb; border-color: #1f6feb; color: white; }
    textarea { width: min(1000px, 100%); min-height: 200px; display: none; margin: 12px 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    table { border-collapse: collapse; width: 100%; background: white; }
    th, td { border: 1px solid #ddd; padding: 10px; vertical-align: top; }
    th { background: #efefe8; text-align: left; }
    audio { width: 260px; display: block; }
    .small { color: #687078; font-size: 12px; line-height: 1.35; word-break: break-word; }
    .tags { display: flex; gap: 5px; flex-wrap: wrap; margin: 6px 0 12px; }
    .tag.active { background: #165dff; color: white; border-color: #165dff; }
    .tag[data-tag="reject"].active, .tag[data-tag="overlap"].active, .tag[data-tag="noise"].active, .tag[data-tag="music"].active, .tag[data-tag="bad_transcript"].active { background: #b42318; border-color: #b42318; }
    .status { color: #687078; font-size: 13px; }
    """
    rows = []
    for item in manifest["references"]:
        dialect_key = f"{item['id']}::dialect"
        quality_key = f"{item['id']}::quality"
        decision_key = f"{item['id']}::decision"
        dialect_buttons = "".join(
            f"<button class='tag' data-key='{dialect_key}' data-tag='{tag}'>{tag}</button>"
            for tag in ["N", "S", "C", "mixed", "unknown"]
        )
        quality_buttons = "".join(
            f"<button class='tag' data-key='{quality_key}' data-tag='{tag}'>{tag}</button>"
            for tag in ["clean", "overlap", "noise", "music", "echo", "bad_transcript"]
        )
        decision_buttons = "".join(
            f"<button class='tag' data-key='{decision_key}' data-tag='{tag}'>{tag}</button>"
            for tag in ["accept", "maybe", "reject"]
        )
        rows.append(
            "<tr>"
            f"<td><div><strong>{html.escape(item['id'])}</strong></div><audio controls preload='none' src='{html.escape(item['file'])}'></audio></td>"
            f"<td><div class='small'>{html.escape(item['source'])}<br>{html.escape(item['text'])}</div></td>"
            f"<td><div class='small'>Dialect</div><div class='tags'>{dialect_buttons}</div>"
            f"<div class='small'>Quality</div><div class='tags'>{quality_buttons}</div>"
            f"<div class='small'>Decision</div><div class='tags'>{decision_buttons}</div></td>"
            "</tr>"
        )

    script = """
    const STORAGE_KEY = "fdb_vi_reference_screening_tags";
    function loadTags() {
      try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}"); }
      catch { return {}; }
    }
    function saveTags(tags) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tags));
      updateStatus(tags);
    }
    function paint(tags) {
      document.querySelectorAll(".tag").forEach(btn => {
        btn.classList.toggle("active", tags[btn.dataset.key] === btn.dataset.tag);
      });
    }
    function updateStatus(tags) {
      const total = new Set(Array.from(document.querySelectorAll(".tag")).map(b => b.dataset.key)).size;
      const done = Object.keys(tags).length;
      document.getElementById("status").textContent = `${done}/${total} fields tagged`;
    }
    document.addEventListener("click", ev => {
      const btn = ev.target.closest(".tag");
      if (!btn) return;
      const tags = loadTags();
      if (tags[btn.dataset.key] === btn.dataset.tag) delete tags[btn.dataset.key];
      else tags[btn.dataset.key] = btn.dataset.tag;
      saveTags(tags);
      paint(tags);
    });
    document.getElementById("export").addEventListener("click", () => {
      const out = document.getElementById("exportText");
      out.style.display = "block";
      out.value = JSON.stringify(loadTags(), null, 2);
      out.select();
    });
    document.getElementById("clear").addEventListener("click", () => {
      if (!confirm("Clear all local tags?")) return;
      localStorage.removeItem(STORAGE_KEY);
      paint({});
      updateStatus({});
      document.getElementById("exportText").style.display = "none";
    });
    const tags = loadTags();
    paint(tags);
    updateStatus(tags);
    """
    return f"""<!doctype html>
<html lang="vi">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vietnamese Reference Screening</title><style>{style}</style></head>
<body>
<h1>Vietnamese Reference Screening</h1>
<p class="note">Screen reference clips before zero-shot cloning. Accept only clean single-speaker clips with clear dialect. Tags are saved in browser localStorage; export JSON when done.</p>
<div class="toolbar"><button id="export" class="export">Export JSON</button><button id="clear">Clear tags</button><span id="status" class="status"></span></div>
<textarea id="exportText" readonly></textarea>
<table><thead><tr><th>Audio</th><th>Source / transcript</th><th>Assessment</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<script>{script}</script>
</body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="outputs/fdb_vi_reference_screening/manifest.json")
    parser.add_argument("--output", default="outputs/fdb_vi_reference_screening/index.html")
    args = parser.parse_args()
    manifest_path = Path(args.manifest)
    output_path = Path(args.output)
    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)
    output_path.write_text(build_html(manifest), encoding="utf-8")
    print(output_path)


if __name__ == "__main__":
    main()
