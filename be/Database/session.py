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

# Get environment setting (development/production)
environment = os.getenv('ENVIRONMENT', 'development').lower()

# Connection pool settings from environment or defaults
# Tune these based on your database server capacity and expected load
POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '10'))  # Number of permanent connections
MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '20'))  # Extra connections when pool is exhausted
POOL_TIMEOUT = int(os.getenv('DB_POOL_TIMEOUT', '30'))  # Seconds to wait for connection
POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '3600'))  # Recycle connections after N seconds

# Create SQLAlchemy engine with optimized connection pool settings
# echo=True enables SQL query logging for debugging (only in development)
# Disabled in production for better performance and cleaner logs
# pool_pre_ping=True: Verify connections are alive before using them (handles dropped connections)
# pool_size: Number of connections to keep in the pool
# max_overflow: How many extra connections can be created beyond pool_size
# pool_timeout: Seconds to wait for a connection from the pool
# pool_recycle: Recycle connections after N seconds to avoid stale connections (important for MSSQL)
engine = create_engine(
    db_url,
    echo=(environment == 'development'),
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE
)

# Create session factory
# autoflush=False: Manual control over when changes are flushed to database
# autocommit=False: Manual control over transaction commits
Session = sessionmaker(autoflush=False, autocommit=False, bind=engine)

# Create declarative base class for all models
# All ORM models should inherit from this Base class
Base = declarative_base()