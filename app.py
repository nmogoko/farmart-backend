from config import Config
from datetime import datetime
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import Request
from sqlalchemy.orm import DeclarativeBase
from utils import generate_token, generate_timestamp, generate_password

import requests


app = Flask(__name__)
config = Config()

# Access environment variables
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATION

# Initialize SQLAlchemy and Flask-Migrate
class Base(DeclarativeBase):
  pass

db = SQLAlchemy(app, model_class=Base)
migrate = Migrate(app, db)


@app.route('/initiate-payment', methods=['POST'])
@generate_token
def initiate_payment():
   data = request.get_json()

   request_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

   headers = {
      "Authorization": "Bearer {}".format(request.token)
   }

   payload = {   
    "BusinessShortCode": config.MPESA_BUSINESS_SHORTCODE,    
    "Password": generate_password(),   
    "Timestamp": generate_timestamp(),    
    "TransactionType": "CustomerPayBillOnline",    
    "Amount": data["amount"],    
    "PartyA": data["phoneNumber"],    
    "PartyB": config.MPESA_BUSINESS_SHORTCODE,   
    "PhoneNumber": data["phoneNumber"],    
    "CallBackURL": "https://511a-5-65-226-119.ngrok-free.app/callback-url",    
    "AccountReference": data["orderId"],    
    "TransactionDesc": "Paying for items in farmart"
   }

   response = requests.post(request_url, json=payload, headers=headers)
   print(response)
    # I need to populate the Requests table with the response data. I will use the response model
   response["order_id"] = data["orderId"]
   response["user_id"] = 1
   response["created_at"] = datetime.now()
   my_request = Request(**response)
   db.session.add(my_request)
   db.session.commit()
   
   return jsonify(response.json()), response.status_code
   
@app.route('/callback-url', methods=["POST"])
def callback_url():
   data = request.get_json()
   print("This is data from the callback")
   print(data)
   # Here I need to populate two tables. first one is transactions second one is callback metadata. I will use the transactions and callback metadata models
   return jsonify(data), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)