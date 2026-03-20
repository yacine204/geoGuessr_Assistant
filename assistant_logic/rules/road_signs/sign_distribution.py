import numpy as np

# min(hue, saturation, value) min(hue, saturation, value)
COLORS = {
    "red": [
        (np.array([0,   150, 100]), np.array([10,  255, 255])),  # lower red
        (np.array([170, 150, 100]), np.array([180, 255, 255])),  # upper red (wraps)
    ],
    "yellow": [
        (np.array([20, 150, 150]), np.array([35, 255, 255])),
    ],
    "white": [
        (np.array([0,  0,   200]), np.array([180, 40, 255])),
    ],
    "blue": [
        (np.array([100, 100, 100]), np.array([130, 255, 255])),
    ],
    "green": [
        (np.array([50, 80, 40]), np.array([90, 255, 200])),
    ],
    "brown": [
        (np.array([10, 80, 50]), np.array([20, 200, 150])),
    ],
    "black": [
        (np.array([0, 0, 0]), np.array([180, 255, 50])),
    ],
    "orange": [
        (np.array([10, 150, 150]), np.array([20, 255, 255])),
    ],
}


SHAPES = {
    "triangle":     {"vertices": 3, "aspect_ratio": (0.8, 1.2)},
    "diamond":      {"vertices": 4, "aspect_ratio": (0.8, 1.2), "rotated": True},
    "rectangle":    {"vertices": 4, "aspect_ratio": (0.0, 0.8)},
    "square":       {"vertices": 4, "aspect_ratio": (0.8, 1.2), "rotated": False},
    "pentagon":     {"vertices": 5, "aspect_ratio": (0.8, 1.2)},
    "octagon":      {"vertices": 8, "aspect_ratio": (0.8, 1.2)},
    "inv_triangle": {"vertices": 3, "aspect_ratio": (0.8, 1.2), "inverted": True},
    "circle":       {"vertices": None, "circularity": (0.75, 1.0)},  # circularity = 4π·A/P²
}


#still in research ,not that accurate 
CONVENTION_RULES = {
    "vienna": [
        {"background": "white",  "shape": "triangle",     "border": "red",   "text_color": None},
        {"background": "yellow", "shape": "triangle",     "border": "red",   "text_color": None},
        {"background": "white",  "shape": "circle",       "border": "red",   "text_color": None},
        {"background": "yellow", "shape": "circle",       "border": "red",   "text_color": None},
        {"background": "blue",   "shape": "circle",       "border": None,    "text_color": "white"},
        {"background": "blue",   "shape": "any",          "border": None,    "text_color": "white"},
    ],
    "mutcd": [
        {"background": "yellow", "shape": "diamond",      "border": "black", "text_color": None},
        {"background": "yellow", "shape": "diamond",      "border": None,    "text_color": None},
        {"background": "white",  "shape": "rectangle",    "border": "black", "text_color": None},
        {"background": "white",  "shape": "rectangle",    "border": None,    "text_color": None},
        {"background": "green",  "shape": "rectangle",    "border": None,    "text_color": "any"},
        {"background": "green",  "shape": "any",          "border": None,    "text_color": "white"},
        {"background": "yellow", "shape": "pentagon",     "border": "black", "text_color": "black"},
        {"background": "orange", "shape": "rectangle",    "border": None,    "text_color": "black"},
    ],
    "ambiguous": [
        {"background": "red",    "shape": "octagon",      "border": "white", "text_color": "white"},
        {"background": "white",  "shape": "inv_triangle", "border": "red",   "text_color": "red"},
    ],
    "shared": [
        {"background": "brown",  "shape": "any",          "border": None,    "text_color": "white"},
    ],
}