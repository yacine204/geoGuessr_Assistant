from dotenv import load_dotenv
import os

env = load_dotenv()

host = os.getenv("DB_HOST")
password = os.getenv("DB_PASSWORD")
username = os.getenv("DB_USERNAME")
name = os.getenv("DB_NAME")


DB_URL = f"postgresql+asyncpg://{username}:{password}@{host}/{name}"