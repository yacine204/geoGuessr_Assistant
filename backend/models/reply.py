from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional

class Reply(SQLModel, table=True):
    reply_id: int | None = Field(primary_key=True, default=None)
    content: str = Field(max_length=100, nullable=False)
    replied_at: datetime = Field(default_factory= lambda: datetime.now(timezone.utc))
    #to check whether the ai taking too long or the ai
    generated_at: datetime 
    image_id: int = Field(foreign_key="image.image_id")
    image: Optional["Image"] = Relationship(back_populates="reply")
