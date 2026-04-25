from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Column, Text

if TYPE_CHECKING:
    from .image import Image

class Reply(SQLModel, table=True):
    reply_id: int | None = Field(primary_key=True, default=None)
    content: str = Field(sa_column=Column(Text, nullable=False))
    replied_at: datetime = Field(default_factory=datetime.utcnow)
    generated_at: datetime 
    image_id: int = Field(foreign_key="image.image_id", unique=True)
    image: Optional["Image"] = Relationship(back_populates="reply")
