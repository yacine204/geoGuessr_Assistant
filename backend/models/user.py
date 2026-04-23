from sqlmodel import SQLModel, Field, Relationship, DateTime, func
from sqlalchemy import Column, Integer
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation import Conversation

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column("user_id", Integer, primary_key=True))
    pseudo: Optional[str] = Field(default=None, unique=True, index=True, nullable=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str

    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True))
    )

    conversations: List["Conversation"] = Relationship(back_populates="user")

class UserCreate(SQLModel):
    pseudo: str | None = None
    email: str
    password: str


class UserRead(SQLModel):
    pseudo: str | None = None
    id: int
    email: str

class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    email: Optional[str] = None

