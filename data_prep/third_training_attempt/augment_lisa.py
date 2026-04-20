from pathlib import Path
import random
import shutil
import cv2
import numpy as np

LISA_ROOT      = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_dataset_us"
GTSRB_ROOT     = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/german_traffic_signs"
OVERSAMPLE_DIR = "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_oversampled"

IMG_EXTS = {".png", ".jpg", ".jpeg"}

def collect_labeled_images(root: str) -> list[Path]:
    imgs = []
    for ext in IMG_EXTS:
        for img in Path(root).rglob(f"*{ext}"):
            if "negatives" in str(img):
                continue
            if img.with_suffix(".txt").exists():
                imgs.append(img)
    return imgs

def augment_image(img: np.ndarray) -> np.ndarray:
    """Apply a random combo of safe augmentations that don't affect boxes."""
    # 1. Random brightness/contrast
    alpha = random.uniform(0.6, 1.4)   # contrast
    beta  = random.randint(-30, 30)     # brightness
    img   = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    # 2. Random horizontal flip (labels need updating — skip, use safe ones only)
    # 3. Gaussian blur
    if random.random() < 0.4:
        k = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)

    # 4. Random hue/saturation shift
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.int32)
    hsv[:, :, 0] = np.clip(hsv[:, :, 0] + random.randint(-10, 10), 0, 179)  # hue
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] + random.randint(-30, 30), 0, 255)  # sat
    img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 5. Add gaussian noise
    if random.random() < 0.3:
        noise = np.random.normal(0, 8, img.shape).astype(np.int16)
        img   = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    return img

# ── Main ──────────────────────────────────────────────────────────────────────
gtsrb_imgs = collect_labeled_images(GTSRB_ROOT)
lisa_imgs  = collect_labeled_images(LISA_ROOT)

target  = len(gtsrb_imgs) - len(lisa_imgs)
to_copy = random.choices(lisa_imgs, k=target)

out = Path(OVERSAMPLE_DIR)
out.mkdir(parents=True, exist_ok=True)

print(f"GTSRB  : {len(gtsrb_imgs)}")
print(f"LISA   : {len(lisa_imgs)}")
print(f"Generating {target} augmented copies ...")

for i, img_path in enumerate(to_copy):
    img = cv2.imread(str(img_path))
    if img is None:
        continue

    aug = augment_image(img)
    stem = f"os_{i:05d}_{img_path.stem}"

    cv2.imwrite(str(out / f"{stem}.png"), aug)
    shutil.copy(img_path.with_suffix(".txt"), out / f"{stem}.txt")  # labels unchanged

    if i % 1000 == 0:
        print(f"  {i}/{target} done ...")

print(f"Done. {len(list(out.glob('*.txt')))} augmented label files written.")