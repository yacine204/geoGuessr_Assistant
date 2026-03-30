from ultralytics import YOLO
from data_types.road_sign_type import SignResult

def detect_signs(image_path:str, model:YOLO)->list[SignResult]:
    results = model(
        source=image_path,
        save=False,
        save_conf=True,
        conf=0.5,
        stream=True,
     
    )
    print("resutls:\n")
    all_results: list[SignResult] = []
    result: SignResult
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
