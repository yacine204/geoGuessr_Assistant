from models import User, UserCreate
from sqlmodel import Session, select
from abc import ABC, abstractmethod
from utils.auth import AuthUtil
from typing import Optional

class UserService:
    #the repo
    def __init__(self, session: Session):
        self.session = session

    def signup(self, user_create: UserCreate):
        # If user exists make a login otherwise make a sign up
        user = self.checkEmail(user_create.email)
        if user:
            if not AuthUtil.verify_password(user_create.password, user.hashed_password):
                raise Exception("Invalid Credentials")
            
            return AuthUtil.create_jwt_token(user.user_id, user.email, user.pseudo)
        
        else:
            hashed = AuthUtil.hash_password(user_create.password)
            new_user = User(email= user_create.email, password=hashed)
            self.session.add(new_user)
            self.session.commit()
            self.session.refresh(new_user)
            return AuthUtil.create_jwt_token(new_user.user_id, new_user.email, new_user.pseudo)
        

    def checkEmail (self, email: str) -> Optional[User]:
        ## Returns true if user exists
        user = self.session.exec(select(User).where(User.email == email)).first()
        return user