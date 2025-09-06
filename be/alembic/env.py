import os
from dotenv import load_dotenv

from logging.config import fileConfig
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Load environment variables from the .env file
load_dotenv()

# Add your project's root directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Your Project's Models ---
# The path is relative to the directory where alembic is run (which should be 'be' in your case).
# Import your Base object.
from Database.session import Base

from Models.BOQReference import BOQReference

from Models.LLD import LLD
from Models.Inventory import *
from Models.Levels import *
from Models.Site import *
from Models.Dismantling import *
from Models.User import *
from Models.BOQReference import *
from Models.Project import *
from Models.Log import *
from Models.ROPLvl1 import *
from Models.ROPLvl2 import *
from Models.RopPackages import *
from Models.ROPProject import *


# Set the target_metadata to the metadata attribute of your Base object.
target_metadata = Base.metadata

# --- Migration Functions ---
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Get the database URL from the environment variable
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get the database URL from the environment variable
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set.")

    connectable = engine_from_config(
        {"sqlalchemy.url": db_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# --- Main Entry Point ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()