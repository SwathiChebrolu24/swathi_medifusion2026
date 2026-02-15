# app/core/seed_db.py
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.core.init_db import init
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed():
    # First, create tables
    init()

    # Create an initial admin user
    db: Session = next(get_db())
    
    if not db.query(User).filter(User.username == "admin").first():
        admin_user = User(
            username="admin",
            password=pwd_context.hash("admin123"),
            full_name="Admin User",
            role="doctor",  # or "admin"
        )
        db.add(admin_user)
        db.commit()
        print("✅ Admin user created: username='admin', password='admin123'")
    else:
        print("⚠ Admin user already exists")

if __name__ == "__main__":
    seed()
