from dotenv import load_dotenv
from pathlib import Path
import os
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from typing import AsyncGenerator

load_dotenv()

host = os.getenv("DB_HOST")
password = os.getenv("DB_PASSWORD")
username = os.getenv("DB_USERNAME")
name = os.getenv("DB_NAME")
port = os.getenv("DB_PORT", "5432")


DB_URL = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{name}"

engine = create_async_engine(DB_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
	async with async_session_maker() as session:
		yield session