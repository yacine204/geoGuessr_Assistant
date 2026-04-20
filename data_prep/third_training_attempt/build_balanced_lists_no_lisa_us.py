from __future__ import annotations

import random
from collections import Counter, defaultdict
from pathlib import Path

SEED = 42
random.seed(SEED)

ROOT = Path("/home/yacine/Desktop/codes/geoGussr-Assistant/traffic_signs_v3")
OUT_DIR = ROOT / "splits_balanced"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# class IDs in merged mapping:
# 0=vienna, 1=mutcd, 2=ambiguous
SPECS = [
    {
        "name": "gtsrb_train",
        "root": ROOT / "german_traffic_signs" / "Train",
        "allowed": {0, 2},
    },
    {
        "name": "gtsrb_test",
        "root": ROOT / "german_traffic_signs" / "Test",
        "allowed": {0, 2},
    },
    {
        "name": "lisa_oversampled",
        "root": ROOT / "lisa_oversampled",
        "allowed": {1, 2},
    },
]

IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".ppm", ".bmp", ".webp"]


def find_image_for_label(label_file: Path) -> Path | None:
    # preferred direct suffix replacement first
    for ext in IMAGE_EXTS:
        img = label_file.with_suffix(ext)
        if img.exists():
            return img

    # fallback by stem wildcard
    for p in label_file.parent.glob(label_file.stem + ".*"):
        if p.suffix.lower() in IMAGE_EXTS:
            return p
    return None


def read_single_class_id(label_file: Path, allowed: set[int]) -> int | None:
    lines = label_file.read_text(errors="ignore").strip().splitlines()
    if not lines:
        return None

    cls_ids = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) != 5:
            return None
        try:
            cid = int(parts[0])
            float(parts[1]); float(parts[2]); float(parts[3]); float(parts[4])
        except ValueError:
            return None
        cls_ids.append(cid)

    uniq = set(cls_ids)
    if len(uniq) != 1:
        return None

    cid = cls_ids[0]
    if cid not in allowed:
        return None
    return cid


def build_balanced_list(name: str, root: Path, allowed: set[int]) -> tuple[Path, Counter]:
    by_class: dict[int, list[Path]] = defaultdict(list)

    for label_file in root.rglob("*.txt"):
        cid = read_single_class_id(label_file, allowed)
        if cid is None:
            continue
        img = find_image_for_label(label_file)
        if img is None:
            continue
        by_class[cid].append(img.resolve())

    if len(by_class) < 2:
        raise RuntimeError(f"{name}: expected 2 classes in {sorted(allowed)}, got {sorted(by_class.keys())}")

    counts = {k: len(v) for k, v in by_class.items()}
    target = min(counts.values())

    selected: list[Path] = []
    final_counts: Counter = Counter()
    for cid in sorted(by_class):
        pool = by_class[cid]
        if len(pool) > target:
            picked = random.sample(pool, target)
        else:
            picked = pool
        selected.extend(picked)
        final_counts[cid] = len(picked)

    random.shuffle(selected)

    out_file = OUT_DIR / f"{name}_balanced.txt"
    out_file.write_text("\n".join(str(p) for p in selected) + "\n")
    return out_file, final_counts


def write_yaml(train_file: Path, val_file: Path) -> Path:
    y = ROOT / "merged_balanced_no_lisa_us.yaml"
    content = f"""# Balanced training without lisa_dataset_us
# classes: 0=vienna, 1=mutcd, 2=ambiguous
path: {ROOT}

train: {train_file}
val: {val_file}

nc: 3
names:
  0: vienna
  1: mutcd
  2: ambiguous
"""
    y.write_text(content)
    return y


def main() -> None:
    outputs: dict[str, Path] = {}
    totals: Counter = Counter()

    for spec in SPECS:
        out_file, class_counts = build_balanced_list(spec["name"], spec["root"], spec["allowed"])
        outputs[spec["name"]] = out_file
        totals.update(class_counts)
        print(f"{spec['name']}: {dict(class_counts)} -> {out_file}")

    # train = balanced gtsrb train + balanced lisa oversampled
    train_paths = []
    for key in ("gtsrb_train", "lisa_oversampled"):
        train_paths.extend(Path(outputs[key]).read_text().strip().splitlines())
    random.shuffle(train_paths)

    train_file = OUT_DIR / "train_balanced_no_lisa_us.txt"
    train_file.write_text("\n".join(train_paths) + "\n")

    # val = balanced gtsrb test
    val_file = OUT_DIR / "val_balanced_no_lisa_us.txt"
    val_file.write_text(outputs["gtsrb_test"].read_text())

    yml = write_yaml(train_file, val_file)

    print("\nCombined files:")
    print(f"  train -> {train_file} ({len(train_paths)} images)")
    print(f"  val   -> {val_file} ({len(val_file.read_text().strip().splitlines())} images)")
    print(f"  yaml  -> {yml}")


if __name__ == "__main__":
    main()
