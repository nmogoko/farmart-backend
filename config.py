from dotenv import load_dotenv
import os

load_dotenv()

# Configuration settings for example db, environment variables
class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATION = False
    CONSUMER_KEY = os.getenv("CONSUMER_KEY")
    CONSUMER_SECRET = os.getenv("CONSUMER_SECRET")
    MPESA_PASSKEY = os.getenv("MPESA_PASSKEY")
    MPESA_BUSINESS_SHORTCODE=os.getenv("MPESA_BUSINESS_SHORTCODE")
    # JWT_SECRET_KEY = '3259a843-5011-4b6c-8880-54b029aaa069'
    # JWT_BLACKLIST_ENABLED = True
    # JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']
    # MAIL_SERVER = 'smtp.gmail.com'
    # MAIL_PORT = 465
    # MAIL_USERNAME = 'remmykiplangat4873@gmail.com'
    # MAIL_PASSWORD = 'shcheihckaenzzkw'
    # MAIL_USE_TLS = False
    # MAIL_USE_SSL = True