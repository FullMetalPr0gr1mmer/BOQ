import os
from dotenv import load_dotenv

from logging.config import fileConfig
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Load environment variables from the .env file
load_dotenv()

from Models.BOQ.BOQReference import *
from Models.BOQ.Dismantling import *
from Models.BOQ.Inventory import *
from Models.BOQ.Levels import *
from Models.BOQ.LLD import *
from Models.BOQ.Site import *
from Models.BOQ.Project import *


from Models.Admin.User import *
from Models.Admin.AuditLog import *


from Models.LE.ROPLvl1 import *
from Models.LE.ROPLvl2 import *
from Models.LE.RopPackages import *
from Models.LE.ROPProject import *



from Models.RAN.RAN_LLD import *
from Models.RAN.RANLvl3 import *
from Models.RAN.RANInventory import *
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

from Models.RAN.RANInventory import *


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