from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation import Conversation
    from .reply import Reply


class Image(SQLModel, table=True):
    image_id: int | None = Field(primary_key=True, default=None)
    storage_key: str | None = Field(default=None)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: int = Field(foreign_key="conversation.conversation_id")
    conversation: Optional["Conversation"] = Relationship(back_populates="images")
    reply: Optional["Reply"] = Relationship(
        back_populates="image",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )
