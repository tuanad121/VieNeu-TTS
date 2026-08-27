# Zero-shot Vietnamese dialect workflow

This code-only workflow helps select clean reference clips, label their perceived
dialect, and test how well VieNeu-TTS preserves that dialect during zero-shot
voice cloning. Generated audio and human assessments stay under `outputs/`,
which is excluded from Git.

## 1. Sample reference candidates

```bash
python sample_reference_candidates.py \
  --out-dir outputs/fdb_vi_reference_screening \
  --count 24
```

The sampler streams the VietSuperSpeech validation split, applies basic duration
and transcript filters, downloads short reference clips, and builds an HTML
screening page.

## 2. Screen references

Open `outputs/fdb_vi_reference_screening/index.html`. For each clip, label:

- dialect: `N`, `S`, `C`, `mixed`, or `unknown`;
- quality: `clean`, `overlap`, `noise`, `music`, `echo`, or `bad_transcript`;
- decision: `accept`, `maybe`, or `reject`.

Use **Export JSON** and save the result as
`outputs/fdb_vi_reference_screening/assessment.json`.

## 3. Run zero-shot cloning and dialect audit

```bash
python generate_accepted_reference_audit.py \
  --screening-manifest outputs/fdb_vi_reference_screening/manifest.json \
  --assessment outputs/fdb_vi_reference_screening/assessment.json \
  --out-dir outputs/fdb_vi_accepted_reference_audit
```

The generator keeps references marked both `accept` and `clean`, trims each to a
short conditioning clip, and synthesizes a fixed prompt suite through
`Vieneu(mode="v3turbo", backend="pytorch")` with `ref_audio`. Open the generated
`index.html` to audit dialect consistency row by row.

## Data note

The workflow code does not redistribute reference or generated audio. Review the
source dataset's terms and obtain any consent or permissions required for your
use case before publishing voices or cloned outputs.
