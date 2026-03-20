from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, List


class Conversation(SQLModel, table=True):
    conversation_id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=100)
    created_at: datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
    user_id : int = Field(foreign_key="user.user_id")
    user: Optional["User"] = Relationship(back_populates="conversations")
    images: List["Image"] = Relationship(back_populates="conversation")