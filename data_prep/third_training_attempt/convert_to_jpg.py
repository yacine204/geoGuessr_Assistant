from pathlib import Path
from PIL import Image

DIRS = [
    "/home/yacine/Desktop/codes/geoGussr-Assistant/datasets/training_v3_dataset/lisa_dataset_us",

]

for folder in DIRS:
    converted = 0
    for png in Path(folder).rglob("*.png"):
        img = Image.open(png).convert("RGB")
        jpg_path = png.with_suffix(".jpg")
        img.save(jpg_path, "JPEG", quality=90)
        png.unlink()
        converted += 1
        if converted % 1000 == 0:
            print(f"  [{Path(folder).name}] {converted} done ...")
    print(f" {Path(folder).name}: {converted} files converted")