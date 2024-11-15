from dotenv import load_dotenv
import os

load_dotenv()



class Config:
    SQLALCHEMY_SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATION = False
    CONSUMER_KEY = os.getenv("CONSUMER_KEY")
    CONSUMER__SECRET = os.getenv("CONSUMER SECRET")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_BUSINESS_SHORTCODE= os.getenv("MPESA_BUSINESS_SHORTCODE")