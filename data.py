import yaml
import os

# MUTCD: stop is ambiguous (looks same in both conventions)
def get_new_class_mutcd(class_name):
    if class_name == "stop":
        return 2  # ambiguous
    elif class_name in ["regulatory", "warning"]:
        return 0  # mutcd
    return None

# Vienna: prio_stop is ambiguous too
def get_new_class_vienna(class_name):
    if class_name == "prio_stop":
        return 2  # ambiguous
    elif class_name.startswith(("forb_", "info_", "mand_", "prio_", "warn_")):
        return 1  # vienna
    return None

def remap_labels(labels_dir, original_classes, remap_fn):
    files = [f for f in os.listdir(labels_dir) if f.endswith(".txt")]
    print(f"Remapping {len(files)} files in {labels_dir}")
    
    for label_file in files:
        filepath = os.path.join(labels_dir, label_file)
        new_lines = []

        with open(filepath) as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                old_id = int(parts[0])
                class_name = original_classes[old_id]
                new_id = remap_fn(class_name)

                if new_id is None:
                    continue

                new_lines.append(f"{new_id} {' '.join(parts[1:])}")

        with open(filepath, "w") as f:
            f.write("\n".join(new_lines))

# load classes
with open("datasets/yolov8_vienna_signs/data.yaml") as f:
    vienna_classes = yaml.safe_load(f)['names']

with open("datasets/yolov8_mutcd_signs/data.yaml") as f:
    mutcd_classes = yaml.safe_load(f)['names']

# remap
remap_labels("datasets/yolov8_vienna_signs/train/labels", vienna_classes, get_new_class_vienna)

remap_labels("datasets/yolov8_mutcd_signs/train/labels", mutcd_classes, get_new_class_mutcd)


print("Done")