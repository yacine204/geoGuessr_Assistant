from .yolo_result_type import Convention, BoxType, Confidence
from dataclasses import dataclass

@dataclass
class SignResult:
    convention: Convention
    Confidence: Confidence
    box: BoxType