from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from .image import Image
    from .user import User


class Conversation(SQLModel, table=True):
    conversation_id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=100)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        index=True
    )
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
    user_id : int = Field(foreign_key="user.user_id")
    user: Optional["User"] = Relationship(back_populates="conversations")
    images: List["Image"] = Relationship(back_populates="conversation")

    