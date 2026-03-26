from ultralytics import YOLO
from helpers.file_parsing import image_yolo_parsing
import os

model = YOLO("yolo_pts/yolov8l.pt")

image_test = '/home/yacine/Desktop/codes/geoGussr-Assistant/tests/archive/compressed_dataset/Aland/canvas_1629777324.jpg'

results = image_yolo_parsing(image_test, model)

os.makedirs("detections/",exist_ok=True)
output_path = f"detections/{os.path.basename(results[0].path)}"
#saving
results[0].save(output_path)