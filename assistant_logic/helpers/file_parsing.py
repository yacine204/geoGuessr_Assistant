from ultralytics import YOLO


def image_yolo_parsing(image_file_path:str, model:YOLO):
    results = model(
        source=image_file_path,
        save=False,
        save_conf=True,
        conf=0.5,
        stream=True,
     
    )
    all_results = []
    for result in results:
        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())
            class_name = model.names[class_id]
            bbox = box.xyxy[0].tolist()
            print(f"Detected: {class_name} | conf: {confidence:.2f} | box: {bbox}")

        result.show()
        all_results.append(result)

    return all_results
