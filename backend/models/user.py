from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import List, Optional

class User(SQLModel, table=True):
    user_id: int | None = Field(primary_key=True, default=None)
    pseudo: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(
        default_factory= lambda: datetime.now(timezone.utc),
        index=True
    )
    updated_at: datetime | None = Field(default=None)
    deleted_at: datetime | None = Field(default=None)
    conversations: List["Conversation"] = Relationship(back_populates="user")

class UserCreate(SQLModel):
    pseudo: str
    email: str
    password: str

class UserRead(SQLModel):
    pseudo: str 
    id: int
    email: str