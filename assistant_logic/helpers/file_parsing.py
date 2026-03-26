from ultralytics import YOLO


def image_yolo_parsing(image_file_path:str, model:YOLO):
    results = model(
        source=image_file_path,
        save=False,
        save_conf=True
    )

    for result in results:
        boxes = result.boxes  # Boxes object for bounding box outputs
        masks = result.masks  # Masks object for segmentation masks outputs
        keypoints = result.keypoints  # Keypoints object for pose outputs
        probs = result.probs  # Probs object for classification outputs
        obb = result.obb  # Oriented boxes object for OBB outputs
        result.show()  # display to screen
    return results
