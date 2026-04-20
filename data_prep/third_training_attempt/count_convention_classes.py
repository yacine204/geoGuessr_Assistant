from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Iterable

SEMANTIC_ORDER = ["vienna", "mutcd", "ambiguous"]

MERGED_MAP = {0: "vienna", 1: "mutcd", 2: "ambiguous"}
GTSRB_2CLASS_MAP = {0: "vienna", 1: "ambiguous"}
LISA_2CLASS_MAP = {0: "mutcd", 1: "ambiguous"}


def iter_yolo_label_files(root: Path) -> Iterable[Path]:
    for txt_file in root.rglob("*.txt"):
        try:
            lines = txt_file.read_text(errors="ignore").strip().splitlines()
        except Exception:
            continue
        if not lines:
            continue

        is_label = True
        for line in lines:
            parts = line.strip().split()
            if len(parts) != 5:
                is_label = False
                break
            try:
                int(parts[0])
                float(parts[1])
                float(parts[2])
                float(parts[3])
                float(parts[4])
            except ValueError:
                is_label = False
                break

        if is_label:
            yield txt_file


def count_class_ids(root: Path) -> Counter:
    counts: Counter = Counter()
    for label_file in iter_yolo_label_files(root):
        lines = label_file.read_text(errors="ignore").strip().splitlines()
        for line in lines:
            class_id = int(line.split()[0])
            counts[class_id] += 1
    return counts


def choose_mapping(root: Path, id_counts: Counter) -> dict[int, str]:
    ids = set(id_counts.keys())
    if 2 in ids:
        return MERGED_MAP
    root_s = str(root).lower()
    if "german_traffic_signs" in root_s or "gtsrb" in root_s:
        return GTSRB_2CLASS_MAP
    if "lisa" in root_s or "mutcd" in root_s:
        return LISA_2CLASS_MAP
    # fallback
    return GTSRB_2CLASS_MAP


def to_semantic_counts(id_counts: Counter, mapping: dict[int, str]) -> Counter:
    out: Counter = Counter()
    for cid, n in id_counts.items():
        name = mapping.get(cid, f"unknown_{cid}")
        out[name] += n
    return out


def print_report(title: str, semantic_counts: Counter, id_counts: Counter) -> None:
    total = sum(semantic_counts.values())
    print(f"\n=== {title} ===")
    print(f"total boxes: {total}")

    for name in SEMANTIC_ORDER:
        n = semantic_counts.get(name, 0)
        pct = (100.0 * n / total) if total else 0.0
        print(f"{name:>10}: {n:>8} ({pct:6.2f}%)")

    print(f"raw class IDs: {dict(sorted(id_counts.items()))}")

    unknown = {k: v for k, v in semantic_counts.items() if k.startswith('unknown_')}
    if unknown:
        print("unknown semantic buckets:", dict(sorted(unknown.items())))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Count Vienna/MUTCD/Ambiguous boxes from YOLO label files."
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[
            "/home/yacine/Desktop/codes/geoGussr-Assistant/traffic_signs_v3/german_traffic_signs",
            "/home/yacine/Desktop/codes/geoGussr-Assistant/traffic_signs_v3/lisa_dataset_us",
            "/home/yacine/Desktop/codes/geoGussr-Assistant/traffic_signs_v3/lisa_oversampled",
        ],
        help="One or more dataset roots to scan.",
    )
    args = parser.parse_args()

    overall_semantic = Counter()
    overall_ids = Counter()
    for root_str in args.roots:
        root = Path(root_str)
        if not root.exists():
            print(f"[skip] missing root: {root}")
            continue
        id_counts = count_class_ids(root)
        mapping = choose_mapping(root, id_counts)
        semantic_counts = to_semantic_counts(id_counts, mapping)
        overall_semantic.update(semantic_counts)
        overall_ids.update(id_counts)
        print_report(str(root), semantic_counts, id_counts)

    print_report("OVERALL", overall_semantic, overall_ids)


if __name__ == "__main__":
    main()
