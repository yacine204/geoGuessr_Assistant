from service.user import UserService
from fastapi import FastAPI
from models import User, UserCreate
controller = FastAPI()

@controller.post('/login')
async def login(user_service: UserService,user_create: UserCreate):
    return await UserService.signup(user_service, user_create)
