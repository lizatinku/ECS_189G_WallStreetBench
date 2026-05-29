"""
Build an annotation-ready CSV directly from .txt response files.

Use this when you have responses/<tag>/<prompt_id>__turn<N>.txt files
but no conversations.jsonl (e.g., ChatGPT was run by hand, or the jsonl was lost).

Usage:
    python build_annotation_csv_from_txt.py responses/ --out annotations_to_fill.csv

Folder layout expected:
    responses/
      qwen/
        C1-P1__turn0.txt
        C1-P1__turn1.txt
        ...
      deepseek/
        ...
      chatgpt/
        ...

The script parses the header line of each .txt file to recover prompt_id,
category, and turn_index. The folder name (tag) becomes the model column —
edit MODEL_NAME_MAP below to map tag -> the human-readable model string you
want in the CSV.
"""
import argparse
import csv
import random
import re
from pathlib import Path


# --- Customize these for your run ----------------------------------------
# Maps folder name (under responses/) -> the model string you want in the CSV.
# Folders not listed here will use the folder name as-is.
MODEL_NAME_MAP = {
    "qwen":     "Qwen3-0.6B",
    "deepseek": "DeepSeek-R1-7B",
    "chatgpt":  "ChatGPT (GPT-5.5)",     
}

ANNOTATORS = ["A1", "A2", "A3", "A4"]
DOUBLE_FRACTION = 0.20
# -------------------------------------------------------------------------

CONSISTENCY_GROUPS = {
    "C1-P1": "C1-P1-group", "C1-P1.v1": "C1-P1-group", "C1-P1.v2": "C1-P1-group",
    "C2-P1": "C2-P1-group", "C2-P1.v1": "C2-P1-group", "C2-P1.v2": "C2-P1-group",
    "C3-P1": "C3-P1-group", "C3-P1.v1": "C3-P1-group", "C3-P1.v2": "C3-P1-group",
    "C4-P1": "C4-P1-group", "C4-P1.v1": "C4-P1-group", "C4-P1.v2": "C4-P1-group",
}

COLUMNS = [
    "prompt_id", "category", "model", "annotator", "is_double", "turn_index",
    "reasoning_quality",
    "err_hallucination", "err_misinterpretation",
    "err_overconfidence", "err_contradiction",
    "uncertainty", "risk_awareness", "tradeoff",
    "depth_on_probe", "turn_coherence",
    "consistency_group", "llm_judge_score", "notes",
    "response_file",
]

# Matches the header line written by run_experiment.py:
# === Prompt ID: C1-P1  |  Category: C1  |  Turn: 0 ===
HEADER_RE = re.compile(
    r"Prompt ID:\s*([\w.\-]+)\s*\|\s*Category:\s*(\w+)\s*\|\s*Turn:\s*(\d+)"
)

# Fallback: parse from filename like C1-P1__turn0.txt
FNAME_RE = re.compile(r"^([\w.\-]+)__turn(\d+)\.txt$")


def parse_txt(path):
    """Return (prompt_id, category, turn_index) for one .txt response file."""
    # Try header first — most reliable
    try:
        head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        m = HEADER_RE.search(head)
        if m:
            return m.group(1), m.group(2), int(m.group(3))
    except Exception:
        pass

    # Fallback to filename
    m = FNAME_RE.match(path.name)
    if m:
        pid = m.group(1)
        turn = int(m.group(2))
        category = pid.split("-")[0]   # C1-P1 -> C1
        return pid, category, turn

    raise ValueError(f"Cannot parse prompt info from {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("responses_root", help="Path to responses/ folder")
    ap.add_argument("--out", default="annotations_to_fill.csv")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    root = Path(args.responses_root)
    rows = []

    for tag_dir in sorted(root.iterdir()):
        if not tag_dir.is_dir():
            continue
        model_name = MODEL_NAME_MAP.get(tag_dir.name, tag_dir.name)

        txt_files = sorted(tag_dir.glob("*.txt"))
        if not txt_files:
            print(f"[skip] no .txt files in {tag_dir}")
            continue

        for path in txt_files:
            try:
                pid, category, turn = parse_txt(path)
            except ValueError as e:
                print(f"[warn] {e}")
                continue

            row = {c: "" for c in COLUMNS}
            row["prompt_id"]    = pid
            row["category"]     = category
            row["model"]        = model_name
            row["turn_index"]   = turn
            row["consistency_group"] = CONSISTENCY_GROUPS.get(pid, "")
            row["response_file"]= f"{tag_dir.name}/{path.name}"
            rows.append(row)

        print(f"[ok] {tag_dir.name} -> {model_name}: {sum(1 for r in rows if r['model']==model_name)} responses")

    if not rows:
        print("No responses found. Check your --responses_root path.")
        return

    # Deterministic ordering for annotator assignment
    rows.sort(key=lambda r: (r["model"], r["prompt_id"], r["turn_index"]))

    # Primary annotators round-robin
    for i, row in enumerate(rows):
        row["annotator"] = ANNOTATORS[i % len(ANNOTATORS)]
        row["is_double"] = 0

    # 20% double annotation
    n_double = int(len(rows) * DOUBLE_FRACTION)
    double_indices = sorted(rng.sample(range(len(rows)), n_double))
    double_rows = []
    for i in double_indices:
        primary = rows[i]
        others = [a for a in ANNOTATORS if a != primary["annotator"]]
        second = rng.choice(others)
        dup = dict(primary)
        dup["annotator"] = second
        dup["is_double"] = 1
        double_rows.append(dup)

    rows.extend(double_rows)
    rows.sort(key=lambda r: (r["prompt_id"], r["turn_index"], r["model"], r["is_double"]))

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    primary_count = sum(1 for r in rows if r["is_double"] == 0)
    double_count  = sum(1 for r in rows if r["is_double"] == 1)
    print(f"\nWrote {args.out}")
    print(f"  Primary annotations: {primary_count}")
    print(f"  Double-annotation rows: {double_count} ({100*double_count/primary_count:.1f}%)")
    print(f"  Per-annotator primary load: ~{primary_count // len(ANNOTATORS)} responses each")


if __name__ == "__main__":
    main()