from pathlib import Path
from PIL import Image
import csv

LISA_ROOT = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_dataset_us"

AMBIGUOUS_TAGS = {"stop", "yield"}  # everything else → MUTCD (0)

all_csv = Path(LISA_ROOT) / "allAnnotations.csv"
annotations: dict = {}

with open(all_csv, newline="") as f:
    reader = csv.reader(f, delimiter=";")
    header = next(reader)
    print("CSV columns:", header)

    for row in reader:
        if len(row) < 6:
            continue
        filename = row[0].strip()
        tag      = row[1].strip().lower()
        try:
            x1, y1, x2, y2 = float(row[2]), float(row[3]), float(row[4]), float(row[5])
        except ValueError:
            continue

        img_path = Path(LISA_ROOT) / filename
        if not img_path.exists():
            continue

        try:
            w, h = Image.open(img_path).size
        except Exception:
            continue

        cx = ((x1 + x2) / 2) / w
        cy = ((y1 + y2) / 2) / h
        bw = (x2 - x1) / w
        bh = (y2 - y1) / h
        cx, cy, bw, bh = (max(0.0, min(1.0, v)) for v in (cx, cy, bw, bh))

        # mark any stop/yield variant as ambiguous (e.g., stopAhead, yieldAhead)
        tag_lower = tag.lower()
        class_id = 1 if any(k in tag_lower for k in AMBIGUOUS_TAGS) else 0  # stop/yield variants → 1, rest → 0

        if img_path not in annotations:
            annotations[img_path] = []
        annotations[img_path].append((class_id, cx, cy, bw, bh))

written = 0
for img_path, boxes in annotations.items():
    label_path = img_path.with_suffix(".txt")
    with open(label_path, "w") as f:
        for cls, cx, cy, bw, bh in boxes:
            f.write(f"{cls} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")
    written += 1

print(f"Done. Wrote {written} label files.")