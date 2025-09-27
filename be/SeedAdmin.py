"""
Admin User Seeding Script

This script creates the initial admin user for the BOQ management system.
It's designed to be run once during system setup to establish the first
administrative account.

Key Features:
- Checks for existing admin user to prevent duplicates
- Validates admin role exists before user creation
- Uses environment variables for secure password handling
- Proper database session management with cleanup

Environment Variables Required:
- ADMIN_PASSWORD: Pre-hashed password for the admin user

Prerequisites:
- Database must be initialized with tables
- Admin role must exist in the roles table
- Environment variables must be properly configured

Usage:
    python SeedAdmin.py

Security Notes:
- The admin password should be pre-hashed using bcrypt
- Store the hashed password in environment variables, not plain text
- This script should only be run in secure environments

Author: [Your Name]
Created: [Date]
Last Modified: [Date]
"""

import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from Database.session import Session  # Session factory from database configuration
import os
from dotenv import load_dotenv

# Import the User and Role models
from Models.Admin.User import User
from Models.Admin.User import Role

# Load environment variables
load_dotenv()
admin_hashed_password = os.getenv("ADMIN_PASSWORD")


def seed_admin():
    """
    Create the initial admin user for the system.

    This function performs the following operations:
    1. Checks if an admin user already exists
    2. Validates that the admin role exists in the database
    3. Creates a new admin user if none exists
    4. Properly manages database sessions and cleanup

    Raises:
        Exception: If admin role doesn't exist or database operations fail

    Returns:
        None: Prints status messages to console
    """
    # Create database session
    db: Session = Session()

    try:
        # Check if admin user already exists
        admin_exists = db.query(User).filter(User.username == 'admin').first()

        # Verify admin role exists
        admin_role = db.query(Role).filter(Role.name == 'admin').first()
        if not admin_role:
            print("Error: Admin role not found. Please create the admin role first.")
            return

        # Create admin user if it doesn't exist
        if admin_exists:
            print("Info: Admin user already exists. No action needed.")
            return
        else:
            # Create new admin user
            admin = User(
                username="admin",
                email="admin@nokia.com",
                hashed_password=admin_hashed_password,
                role_id=admin_role.id,  # Link to admin role via foreign key
            )

            # Add user to database
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print("Success: Admin user created successfully.")

    except Exception as e:
        # Rollback transaction on error
        db.rollback()
        print(f"Error: Failed to create admin user: {str(e)}")
        raise

    finally:
        # Always close database session
        db.close()


if __name__ == "__main__":
    """
    Main entry point for the seeding script.
    Execute the admin user creation process.
    """
    seed_admin()