from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db.database import SessionLocal
from db.model import User              

# =========================
# CONFIG
# =========================

SECRET_KEY = "SUPER_SECRET_KEY_CHANGE_ME"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# =========================
# IN-MEMORY USERS (DEMO ONLY)
# =========================
# ❗ Production me DB + hashed passwords use hote hain

fake_users_db = {
    "admin": {
        "username": "admin",
        "password": "admin123"   # 🔥 DEMO ONLY (plain)
    }
}

# =========================
# JWT TOKEN CREATION
# =========================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# AUTHENTICATE USER
# =========================

def authenticate_user(username: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False

        # ⚠️ DEMO comparison – unchanged as requested
        if user.password_hash != password:
            return False

        return {
            "id": user.id,
            "username": user.username
        }
    finally:
        db.close()

# =========================
# TOKEN VERIFICATION (PROTECT ROUTES)
# =========================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")

        if username is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception

        return {
            "id": user.id,
            "username": user.username
        }
    finally:
        db.close()