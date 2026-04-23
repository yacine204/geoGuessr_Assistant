from ..models import User, UserCreate
from sqlmodel import Session, select
from abc import ABC, abstractmethod
from ..utils.auth import AuthUtil
from typing import Optional

class UserService:
    #the repo
    def __init__(self, session: Session):
        self.session = session

    