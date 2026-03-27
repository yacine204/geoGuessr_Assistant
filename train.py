from ultralytics import YOLO

model = YOLO("yolov8m.pt")
model.train(
    data="data.yaml",
    epochs=50,
    imgsz=640,
    batch=16,
    fraction=0.9,        
    project="runs",
    name="signs_v1"
)