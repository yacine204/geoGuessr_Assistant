import os
from collections import defaultdict

def analyze_yolo_dataset(split_path, class_names):
    """Analyze one split (train/val/test) of a YOLO dataset."""
    
    # Get image and label file paths
    image_dir = os.path.join(split_path, 'images')
    label_dir = os.path.join(split_path, 'labels')
    
    if not os.path.exists(image_dir) or not os.path.exists(label_dir):
        print(f"Skipping {split_path}: missing images or labels folder")
        return None
    
    # Create a mapping of image files to label files
    image_files = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
    
    stats = {
        'total_images': len(image_files),
        'total_annotations': 0,
        'class_counts': defaultdict(int),
        'images_without_labels': 0,
        'labels_found': 0
    }
    
    for img in image_files:
        label_file = os.path.splitext(img)[0] + '.txt'
        label_path = os.path.join(label_dir, label_file)
        
        if os.path.exists(label_path):
            stats['labels_found'] += 1
            with open(label_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        stats['class_counts'][class_id] += 1
                        stats['total_annotations'] += 1
        else:
            stats['images_without_labels'] += 1
    
    return stats

# Define your dataset splits with full paths
dataset_splits = {
    'train': 'datasets/your_merged_dataset/train',
    'val': 'datasets/your_merged_dataset/val',
    'test': 'datasets/your_merged_dataset/test'
}

# Map class IDs to meaningful names
class_names = {
    0: 'MUTCD',
    1: 'Vienna',
    2: 'Ambiguous'
}

# Analyze each split and combine totals
combined_stats = defaultdict(int)
split_stats = {}

for split_name, split_path in dataset_splits.items():
    print(f"\nAnalyzing {split_name.upper()} split...")
    stats = analyze_yolo_dataset(split_path, class_names)
    if stats:
        split_stats[split_name] = stats
        
        # Add to combined totals
        for key in ['total_images', 'total_annotations', 'labels_found']:
            combined_stats[key] += stats.get(key, 0)
        for class_id, count in stats['class_counts'].items():
            combined_stats[class_id] += count
else:
    print(f"Folder {split_path} not found")

# --- Print Final Statistics ---
print("\n" + "="*50)
print("FINAL DATASET STATISTICS")
print("="*50)

print(f"\nTotal images: {combined_stats['total_images']}")
print(f"Total annotations (bounding boxes): {combined_stats['total_annotations']}")

print("\nClass Distribution:")
for class_id, name in class_names.items():
    print(f"   - {name}: {combined_stats[class_id]} instances")

print("\n📁 Split Distribution:")
for split_name in ['train', 'val', 'test']:
    if split_name in split_stats:
        s = split_stats[split_name]
        print(f"   {split_name.capitalize()}: {s['total_images']} images, {s['total_annotations']} annotations")
    else:
        print(f"   {split_name.capitalize()}: not available")