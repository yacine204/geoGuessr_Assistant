from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional


class Image(SQLModel, table=True):
    image_id: int | None = Field(primary_key=True, default=None)
    storage_key: str | None = Field(default=None)
    uploaded_at: datetime = Field(default= lambda: datetime.now(timezone.utc))
    conversation_id: int = Field(foreign_key="conversation.conversation_id")
    conversation: Optional["Conversation"] = Relationship(back_populates="images")
