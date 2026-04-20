"""
Dataset Health Checker
======================
Validates YOLO-format label files across multiple datasets before training.

For each dataset it checks:
  - All .txt label files are well-formed (5 columns, valid floats, normalized coords)
  - All class IDs match the expected classes for that dataset
  - No images are missing their paired label file

Usage:
    python check_labels.py

Expected label format (YOLO):
    <class_id> <cx> <cy> <width> <height>   ← all values normalized 0.0–1.0
"""

import os
from pathlib import Path
from collections import defaultdict

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LISA_ROOT  = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_dataset_us"
GTSRB_ROOT = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/german_traffic_signs"

GTSRB_CLASSES = {0: "Vienna", 1: "Ambiguous"}
LISA_CLASSES  = {0: "MUTCD",  1: "Ambiguous"}
# ──────────────────────────────────────────────────────────────────────────────


def check_dataset(root: str, class_names: dict, label: str):
    print(f"\n{'═'*55}")
    print(f"  {label}: {root}")
    print(f"{'═'*55}")

    txt_files       = list(Path(root).rglob("*.txt"))
    # filter out non-label txts (yaml companions, image lists, readme)
    label_files     = [f for f in txt_files if f.suffix == ".txt"
                       and f.stat().st_size > 0
                       and _looks_like_label(f)]

    total_files     = len(label_files)
    total_boxes     = 0
    class_counts    = defaultdict(int)
    bad_files       = []   # files with out-of-range values
    empty_files     = []   # .txt with no valid lines
    unknown_classes = set()

    for lf in label_files:
        lines = lf.read_text().strip().splitlines()
        valid_lines = 0
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                bad_files.append((lf, f"wrong column count: {line!r}"))
                continue
            try:
                cid, cx, cy, bw, bh = int(parts[0]), float(parts[1]), \
                                       float(parts[2]), float(parts[3]), float(parts[4])
            except ValueError:
                bad_files.append((lf, f"parse error: {line!r}"))
                continue

            # range check
            if not all(0.0 <= v <= 1.0 for v in (cx, cy, bw, bh)):
                bad_files.append((lf, f"out of range: {line!r}"))
                continue

            if cid not in class_names:
                unknown_classes.add(cid)

            class_counts[cid] += 1
            total_boxes += 1
            valid_lines += 1

        if valid_lines == 0:
            empty_files.append(lf)

    # ── Report ────────────────────────────────────────────────────────────────
    print(f"  Label files found : {total_files}")
    print(f"  Total boxes       : {total_boxes}")
    print(f"  Avg boxes/file    : {total_boxes/total_files:.1f}" if total_files else "  Avg boxes/file: N/A")

    print(f"\n  Class distribution:")
    for cid in sorted(class_counts):
        name  = class_names.get(cid, f"UNKNOWN({cid})")
        count = class_counts[cid]
        pct   = count / total_boxes * 100 if total_boxes else 0
        bar   = "█" * int(pct / 2)
        print(f"    [{cid}] {name:<12} {count:>6} boxes  {pct:5.1f}%  {bar}")

    if unknown_classes:
        print(f"\n  Unknown class IDs found: {sorted(unknown_classes)}")
    else:
        print(f"\n  All class IDs valid")

    if bad_files:
        print(f"\n  {len(bad_files)} bad lines found (first 5):")
        for f, reason in bad_files[:5]:
            print(f"     {f.name}: {reason}")
    else:
        print(f"  ✅ No malformed lines")

    if empty_files:
        print(f"\n  {len(empty_files)} empty label files (first 5):")
        for f in empty_files[:5]:
            print(f"     {f}")
    else:
        print(f"  No empty label files")

    # ── Images without labels ─────────────────────────────────────────────────
    img_extensions = {".png", ".jpg", ".jpeg"}
    imgs_without_labels = []
    for ext in img_extensions:
        for img in Path(root).rglob(f"*{ext}"):
            if "negatives" in str(img):
                continue
            if not img.with_suffix(".txt").exists():
                imgs_without_labels.append(img)

    if imgs_without_labels:
        print(f"\n  {len(imgs_without_labels)} images have no label file (first 5):")
        for f in imgs_without_labels[:5]:
            print(f"     {f.name}")
    else:
        print(f" Every image has a label file")


def _looks_like_label(f: Path) -> bool:
    """Heuristic: a real label file has lines starting with a digit."""
    try:
        first_line = f.read_text().strip().splitlines()[0]
        return first_line[0].isdigit()
    except Exception:
        return False


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    check_dataset(GTSRB_ROOT, GTSRB_CLASSES, "GTSRB")
    check_dataset(LISA_ROOT,  LISA_CLASSES,  "LISA")
    check_dataset(
    "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_oversampled",
    {0: "MUTCD", 1: "Ambiguous"},
    "LISA Oversampled"
)
    print(f"\n{'═'*55}")
    print("  Done. Fix any before training.")
    print(f"{'═'*55}\n")