import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import create_engine  # You might need this to create the engine
from Database.session import Session  # Assuming this is your session factory
import os
from dotenv import load_dotenv

# Import the User and Role models
from Models.Admin.User import User
from Models.Admin.User import Role  # Make sure you import the Role model

load_dotenv()
admin_hashed_password = os.getenv("ADMIN_PASSWORD")


def seed_admin():
    db: Session = Session()
    admin_exists = db.query(User).filter(User.username == 'admin').first()

    # Check if the 'admin' role exists and get its ID
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    if not admin_role:
        print("Admin role not found. Please create it first.")
        db.close()
        return

    if admin_exists:
        db.close()
        print("Admin user already exists.")
        return
    else:
        admin = User(
            username="admin",
            email="admin@nokia.com",
            hashed_password=admin_hashed_password,
            # ✅ Correct way: use the foreign key 'role_id' to set the integer ID
            role_id=admin_role.id,
            # Or, if you wanted to use the relationship:
            # role=admin_role
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        db.close()
        print("Admin user created.")


if __name__ == "__main__":
    seed_admin()