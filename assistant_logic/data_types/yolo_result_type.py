from dataclasses import dataclass
from typing import Literal

@dataclass
class BoxType:
    x1: int
    x2: int
    y1: int
    y2: int 
    c: float
    w: float
    h: float
    cx: float
    cy: float
    conf: float
    cls: int

    @property
    def xyxy(self)-> tuple[int, int, int, int]:
        return(self.x1, self.y1, self.x2, self.y2)
    
    @property
    def xywh(self)-> tuple[float, float, float, float]:
        return (self.cx, self.cy, self.w, self.h)


type Convention = Literal["vienna", "mutcd", "ambiguous"]

@dataclass
class Confidence:
    value: float
    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.value}")