import os, shutil, random

def split_dataset(dataset_name, val_ratio=0.2):
    base = f"datasets/{dataset_name}"
    for folder in ["valid/images", "valid/labels"]:
        os.makedirs(f"{base}/{folder}", exist_ok=True)

    images = os.listdir(f"{base}/train/images")
    random.shuffle(images)
    val_images = images[:int(len(images) * val_ratio)]

    for img_file in val_images:
        stem = os.path.splitext(img_file)[0]
        shutil.move(f"{base}/train/images/{img_file}", f"{base}/valid/images/{img_file}")
        label_file = stem + ".txt"
        label_path = f"{base}/train/labels/{label_file}"
        if os.path.exists(label_path):
            shutil.move(label_path, f"{base}/valid/labels/{label_file}")

    print(f"{dataset_name}: moved {len(val_images)} images to valid")

split_dataset("vienna")
split_dataset("mutcd")