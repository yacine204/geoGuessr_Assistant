import cv2
import numpy as np

def is_yield_or_stop(image_crop):
    hsv = cv2.cvtColor(image_crop, cv2.COLOR_BGR2HSV)
    
    red_lower1 = np.array([0, 100, 100])
    red_upper1 = np.array([10, 255, 255])
    red_lower2 = np.array([160, 100, 100])
    red_upper2 = np.array([180, 255, 255])
    
    red_mask = cv2.inRange(hsv, red_lower1, red_upper1) + \
               cv2.inRange(hsv, red_lower2, red_upper2)
    
    red_ratio = np.sum(red_mask > 0) / red_mask.size
    
    # if heavily red, likely stop or yield → ambiguous
    if red_ratio > 0.3:
        return True
    return False