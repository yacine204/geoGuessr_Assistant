import random
import os

def verify_remap(labels_dir, expected_classes={0, 1, 2}):
    files = [f for f in os.listdir(labels_dir) if f.endswith(".txt")]
    sample = random.sample(files, min(10, len(files)))
    
    print(f"Checking {labels_dir}:")
    for fname in sample:
        with open(os.path.join(labels_dir, fname)) as f:
            lines = f.readlines()
        classes_found = set(int(l.split()[0]) for l in lines if l.strip())
        unexpected = classes_found - expected_classes
        if unexpected:
            print(f"  fail {fname} has unexpected classes: {unexpected}")
        else:
            print(f"  success {fname} → classes: {classes_found}")

verify_remap("datasets/yolov8_vienna_signs/train/labels")
verify_remap("datasets/yolov8_mutcd_signs/train/labels")
