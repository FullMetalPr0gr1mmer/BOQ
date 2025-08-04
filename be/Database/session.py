from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os
from dotenv import load_dotenv
load_dotenv()
db_url=os.getenv('DATABASE_URL')

engine=create_engine(db_url,echo=True)
Session=sessionmaker(autoflush=False,autocommit=False,bind=engine)
Base=declarative_base()