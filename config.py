from dotenv import load_dotenv
import os

load_dotenv()



class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CONSUMER_KEY = os.getenv("CONSUMER_KEY", "default_consumer_key")
    CONSUMER_SECRET = os.getenv("CONSUMER_SECRET", "default_consumer_secret")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY", "default_passkey")
    MPESA_BUSINESS_SHORTCODE= os.getenv("MPESA_BUSINESS_SHORTCODE", "default_shortcode")