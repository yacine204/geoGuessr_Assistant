import os
import pandas as pd
from pathlib import Path
from PIL import Image

# ─── CONFIG ───────────────────────────────────────────────────────────────────
LISA_ROOT   = "./datasets/lisa_dataset_us"    # root of lisa_dataset_us/
FRAME_SKIP  = 5      # keep 1 out of every N frames per track (reduces redundancy)
GTSRB_ROOT  = "./datasets/german_traffic_signs"  # path to your GTSRB dataset root (for merged YAML)
# ──────────────────────────────────────────────────────────────────────────────

# 2 classes:
#   0 → MUTCD      (everything except stop/yield variants)
#   1 → Ambiguous  (any tag containing "stop" or "yield")

AMBIGUOUS_KEYWORDS = ("stop", "yield")

def remap_class(tag: str) -> int:
    if any(kw in tag.lower() for kw in AMBIGUOUS_KEYWORDS):
        return 1  # Ambiguous
    return 0      # MUTCD


def get_image_size(img_path: str, cache: dict):
    if img_path in cache:
        return cache[img_path]
    try:
        with Image.open(img_path) as img:
            cache[img_path] = img.size  # (W, H)
            return img.size
    except Exception:
        cache[img_path] = None
        return None


def find_annotation_csvs(lisa_root: str) -> list:
    """
    Recursively find all frameAnnotations*.csv files under lisa_root.
    Each vid* and aiua* subfolder has one inside its annotations subfolder.
    """
    csvs = []
    for p in Path(lisa_root).rglob("frameAnnotations*.csv"):
        if "negatives" not in str(p):
            csvs.append(p)
    return sorted(csvs)


def convert_all(lisa_root: str, frame_skip: int):
    csvs = find_annotation_csvs(lisa_root)
    print(f"\nFound {len(csvs)} frameAnnotations CSV files\n")

    size_cache  = {}
    total_rows  = 0
    total_kept  = 0
    total_skip  = 0
    total_noimg = 0

    for csv_path in csvs:
        # The images live in the same folder as the CSV
        img_dir = csv_path.parent

        try:
            df = pd.read_csv(csv_path, sep=";")
        except Exception as e:
            print(f"  Could not read {csv_path}: {e}")
            continue

        df.columns = [c.strip() for c in df.columns]

        # Required columns check
        required = {"Filename", "Annotation tag",
                    "Upper left corner X", "Upper left corner Y",
                    "Lower right corner X", "Lower right corner Y",
                    "Origin track", "Origin track frame number"}
        if not required.issubset(set(df.columns)):
            print(f"  Skipping {csv_path.name} — missing columns")
            continue

        total_rows += len(df)

        # ── Per-track frame skip ───────────────────────────────────────────
        # Group by track name, keep rows where track_frame_number % FRAME_SKIP == 0
        # This kills redundant consecutive frames while preserving all tracks.
        df["_track_frame"] = pd.to_numeric(
            df["Origin track frame number"], errors="coerce"
        ).fillna(0).astype(int)

        df_filtered = df[df["_track_frame"] % frame_skip == 0].copy()
        total_skip += len(df) - len(df_filtered)

        for _, row in df_filtered.iterrows():
            filename  = row["Filename"]
            tag       = row["Annotation tag"]
            x1        = int(row["Upper left corner X"])
            y1        = int(row["Upper left corner Y"])
            x2        = int(row["Lower right corner X"])
            y2        = int(row["Lower right corner Y"])

            img_path  = str(img_dir / filename)
            size      = get_image_size(img_path, size_cache)

            if size is None:
                total_noimg += 1
                continue

            W, H = size
            class_id = remap_class(tag)

            cx = ((x1 + x2) / 2) / W
            cy = ((y1 + y2) / 2) / H
            bw = (x2 - x1) / W
            bh = (y2 - y1) / H

            cx, cy, bw, bh = (max(0.0, min(1.0, v)) for v in (cx, cy, bw, bh))

            label_path = Path(img_path).with_suffix(".txt")
            with open(label_path, "a") as f:
                f.write(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

            total_kept += 1

        print(f"  ✓ {csv_path.parent.parent.name}/{csv_path.parent.name[:40]}")

    print(f"""
  ─────────────────────────────────
  Total annotation rows  : {total_rows}
  Skipped (frame skip)   : {total_skip}
  Skipped (image missing): {total_noimg}
  Labels written         : {total_kept}
  ─────────────────────────────────""")


def write_image_list(lisa_root: str) -> str:
    """Write a flat list of all image paths (excluding negatives) for the YAML."""
    all_images = []
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for p in Path(lisa_root).rglob(ext):
            if "negatives" not in str(p):
                all_images.append(str(p.resolve()))

    list_path = str(Path(lisa_root) / "lisa_images.txt")
    with open(list_path, "w") as f:
        for p in all_images:
            f.write(p + "\n")
    print(f"\n  Image list → {list_path}  ({len(all_images)} images)")
    return list_path


def write_lisa_yaml(lisa_root: str, img_list_path: str):
    yaml = f"""# YOLOv8 - LISA dataset (2 classes, frame_skip={FRAME_SKIP})
path: {str(Path(lisa_root).resolve())}

train: {img_list_path}
val:   {img_list_path}   # replace with a proper val split

nc: 2

names:
  0: MUTCD
  1: Ambiguous
"""
    out = str(Path(lisa_root) / "lisa.yaml")
    Path(out).write_text(yaml)
    print(f"  LISA YAML  → {out}")


def write_merged_yaml(lisa_root: str, gtsrb_root: str, img_list_path: str):
    yaml = f"""# YOLOv8 - MERGED GTSRB + LISA (3 classes)
#
# Run remap_for_merge.py BEFORE training with this file!
#
#   Class mapping after remap:
#     0 = Vienna     (GTSRB non-ambiguous)
#     1 = MUTCD      (LISA non-ambiguous)
#     2 = Ambiguous  (stop + yield, both datasets)

path: /

train:
  - {str((Path(gtsrb_root) / "Train").resolve())}
  - {img_list_path}

val:
  - {str((Path(gtsrb_root) / "Test").resolve())}

nc: 3

names:
  0: Vienna
  1: MUTCD
  2: Ambiguous
"""
    out = str(Path(lisa_root) / "merged.yaml")
    Path(out).write_text(yaml)
    print(f"  Merged YAML→ {out}")


def write_remap_script(lisa_root: str, gtsrb_root: str):
    script = f"""import os
from pathlib import Path

# Remaps .txt label files from per-dataset 2-class numbering
# to unified 3-class merged numbering.
#
# GTSRB:  0(Vienna) -> 0   |  1(Ambiguous) -> 2
# LISA:   0(MUTCD)  -> 1   |  1(Ambiguous) -> 2

GTSRB_ROOT = r"{str(Path(gtsrb_root).resolve())}"
LISA_ROOT  = r"{str(Path(lisa_root).resolve())}"

GTSRB_MAP = {{0: 0, 1: 2}}
LISA_MAP  = {{0: 1, 1: 2}}

def remap_labels(root: str, class_map: dict, label: str):
    count = 0
    for txt_file in Path(root).rglob("*.txt"):
        # skip yaml companion files or image lists
        if txt_file.suffix != ".txt":
            continue
        lines = txt_file.read_text().strip().splitlines()
        if not lines:
            continue
        new_lines = []
        for line in lines:
            parts = line.strip().split()
            if not parts:
                continue
            old_id = int(parts[0])
            new_id = class_map.get(old_id, old_id)
            new_lines.append(" ".join([str(new_id)] + parts[1:]))
        txt_file.write_text("\\n".join(new_lines) + "\\n")
        count += 1
    print(f"  {{label}}: remapped {{count}} label files")

print("Remapping GTSRB labels...")
remap_labels(GTSRB_ROOT, GTSRB_MAP, "GTSRB")

print("Remapping LISA labels...")
remap_labels(LISA_ROOT, LISA_MAP, "LISA")

print(\"\"\"
Done! Unified class numbering:
  0 = Vienna
  1 = MUTCD
  2 = Ambiguous

Now train:
  yolo task=detect mode=train model=yolov8n.pt data=merged.yaml epochs=50 imgsz=640
\"\"\")
"""
    out = str(Path(lisa_root) / "remap_for_merge.py")
    Path(out).write_text(script)
    print(f"  Remap script→ {out}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"LISA root  : {Path(LISA_ROOT).resolve()}")
    print(f"GTSRB root : {Path(GTSRB_ROOT).resolve()}")
    print(f"Frame skip : every {FRAME_SKIP} frames per track")

    print("\n[1/4] Converting annotations...")
    convert_all(LISA_ROOT, FRAME_SKIP)

    print("\n[2/4] Writing image list...")
    img_list = write_image_list(LISA_ROOT)

    print("\n[3/4] Writing YAML files...")
    write_lisa_yaml(LISA_ROOT, img_list)
    write_merged_yaml(LISA_ROOT, GTSRB_ROOT, img_list)

    print("\n[4/4] Writing remap script...")
    write_remap_script(LISA_ROOT, GTSRB_ROOT)

    print("""
══════════════════════════════════════════
  FULL WORKFLOW
══════════════════════════════════════════
  1. GTSRB (already done):
       python convert_to_yolo.py
       → Vienna(0) / Ambiguous(1)

  2. LISA (just ran):
       python convert_lisa.py
       → MUTCD(0) / Ambiguous(1)

  3. Remap to unified 3-class:
       python remap_for_merge.py
       → Vienna(0) / MUTCD(1) / Ambiguous(2)

  4. Train merged:
       yolo task=detect mode=train \\
            model=yolov8n.pt \\
            data=merged.yaml \\
            epochs=50 imgsz=640
══════════════════════════════════════════
""")