from ..service.user import UserService
from fastapi import FastAPI
from ..models.user import User, UserCreate

user_controller = FastAPI()

