"""
Database Session Configuration

This module handles the SQLAlchemy database connection and session management
for the BOQ management system. It sets up the database engine, session factory,
and base model class used throughout the application.

Key Components:
1. Database Engine: SQLAlchemy engine with connection pooling
2. Session Factory: Creates database sessions for transactions
3. Base Model: Declarative base class for all ORM models

Configuration:
- Database URL loaded from environment variables
- Echo mode enabled for SQL query logging (useful for development)
- Sessions configured without auto-commit and auto-flush for explicit control

Environment Variables Required:
- DATABASE_URL: Complete database connection string
  Format examples:
  - PostgreSQL: postgresql://user:password@localhost:5432/dbname
  - MySQL: mysql+pymysql://user:password@localhost:3306/dbname
  - SQLite: sqlite:///./test.db

Usage:
    from Database.session import Session, Base, engine

    # Create a new session
    db = Session()
    try:
        # Database operations
        result = db.query(Model).all()
        db.commit()
    finally:
        db.close()

Author: [Kareem Hosny]
Created: [Date]
Last Modified: [Date]
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get database URL from environment variables
db_url = os.getenv('DATABASE_URL')

# Create SQLAlchemy engine
# echo=True enables SQL query logging for debugging
engine = create_engine(db_url, echo=True)

# Create session factory
# autoflush=False: Manual control over when changes are flushed to database
# autocommit=False: Manual control over transaction commits
Session = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# Create declarative base class for all models
# All ORM models should inherit from this Base class
Base = declarative_base()