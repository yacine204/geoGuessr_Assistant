from ultralytics import YOLO
from helpers.file_parsing import detect_signs
from data_types.road_sign_type import SignResult
import os

model = YOLO("yolo_pts/geotrouvetout_weights/car_brand.pt")

image_test = '/home/yacine/Desktop/codes/geoGussr-Assistant/tests2/car_test.webp'

results: SignResult = detect_signs(image_test, model)

os.makedirs("detections/",exist_ok=True)
output_path = f"detections/{os.path.basename(results[0].path)}"
#saving
results[0].save(output_path)

##load countries
##def load_countries(result: list):

##init with their distribution 