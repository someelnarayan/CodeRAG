from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

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
    user = fake_users_db.get(username)

    if not user:
        return False

    # 🔥 Simple password check (demo)
    if password != user["password"]:
        return False

    return user

# =========================
# TOKEN VERIFICATION (PROTECT ROUTES)
# =========================

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return username

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalid or expired"
        )
