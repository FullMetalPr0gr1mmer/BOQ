# import bcrypt
# from sqlalchemy.orm import Session
#
# from APIs.Core import pwd_context
# from Models.User import *
# from Database.session import Session
# import os
# from dotenv import load_dotenv
#
# from Models.User import User
#
# load_dotenv()
# admin_hashed_password=os.getenv("ADMIN_PASSWORD")
#
#
# def seed_admin():
#     db:Session= Session()
#     admin_exists = db.query(User).filter(User.username == 'admin').first()
#     if admin_exists:
#         db.close()
#         print("Admin Already Exists")
#         return
#     else:
#         admin = User(
#             username="admin",
#             email="admin@nokia.com",
#             hashed_password=pwd_context.hash(admin_hashed_password),
#             role="admin",
#         )
#         db.add(admin)
#         db.commit()
#         db.refresh(admin)
#         db.close()
#         print("Admin Created")
# if __name__ == "__main__":
#     seed_admin()
