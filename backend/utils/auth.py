import bcrypt
from jose import jwt
from datetime import datetime, timedelta

secret_key = "reqreq"
algorithm = "HS256"
access_token_expiration = 60

class AuthUtil:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())

    @staticmethod
    def create_jwt_token(user_id: int, email: str, pseudo: str) -> str:
        expire = datetime.utcnow + timedelta(minutes=access_token_expiration)
        payload = {"sub": {user_id: str(user_id), email: email, pseudo: pseudo}, "exp": expire}
        return jwt.encode(payload, secret_key, algorithm= algorithm)
    

    @staticmethod
    def validate_jwt_token(token: str) -> dict:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
