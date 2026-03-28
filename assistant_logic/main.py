from ultralytics import YOLO
from helpers.file_parsing import image_yolo_parsing
import os

model = YOLO("yolo_pts/best2.pt")

image_test = '/home/yacine/Desktop/codes/geoGussr-Assistant/tests2/europe_road_signs.jpg'

results = image_yolo_parsing(image_test, model)

os.makedirs("detections/",exist_ok=True)
output_path = f"detections/{os.path.basename(results[0].path)}"
#saving
results[0].save(output_path)

