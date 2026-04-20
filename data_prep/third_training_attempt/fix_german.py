from pathlib import Path

GTSRB_ROOT = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/german_traffic_signs"

deleted = []
for ext in (".png", ".jpg", ".jpeg"):
    for img in Path(GTSRB_ROOT).rglob(f"*{ext}"):
        if "negatives" in str(img):
            continue
        if not img.with_suffix(".txt").exists():
            deleted.append(img)
            img.unlink()

print(f"Deleted {len(deleted)} unlabeled images")
for f in deleted:
    print(f"  {f}")