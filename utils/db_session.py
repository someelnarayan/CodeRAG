from db.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        return db   # 🔥 yield NAHI
    finally:
        pass
