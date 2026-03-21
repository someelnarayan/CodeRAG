from passlib.context import CryptContext

# bcrypt config
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# 🔹 Hash password (REGISTER ke time use hoga)
def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    return pwd_context.hash(password)


# 🔹 Verify password (LOGIN ke time use hoga)
def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False  # agar DB me null ya empty hai
    try:
        return pwd_context.verify(password, hashed)
    except Exception as e:
        print("Password verify error:", e)
        return False