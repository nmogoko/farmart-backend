from config import Config
from datetime import datetime
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import Request, db, Transaction, CallbackMetadatum
from utils import generate_token, generate_timestamp, generate_password

import requests


app = Flask(__name__)
config = Config()

# Access environment variables
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATION

migrate = Migrate(app, db)
db.init_app(app)

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
    "CallBackURL": "https://b28f8200abe4a6120bc978908659ada0.serveo.net/callback-url",    
    "AccountReference": data["orderId"],    
    "TransactionDesc": "Paying for items in farmart"
   }

   response = requests.post(request_url, json=payload, headers=headers)
 
    # I need to populate the Requests table with the response data. I will use the response model
   # Check if the response was successful
   if response.status_code == 200:
        # Parse the response JSON into a dictionary
        response_data = response.json()

        # Add additional fields to the response data dictionary
        response_data["order_id"] = data["orderId"]
        response_data["user_id"] = 1
        response_data["created_at"] = datetime.now()

        # Now, use response_data to populate the Requests table
        # Example: assuming you have a Requests model
        new_request = Request(
            order_id=response_data["order_id"],
            user_id=response_data["user_id"],
            MerchantRequestID=response_data.get("MerchantRequestID"),
            CheckoutRequestID=response_data.get("CheckoutRequestID"),
            ResponseCode=response_data.get("ResponseCode"),
            ResponseDescription=response_data.get("ResponseDescription"),
            CustomerMessage=response_data.get("CustomerMessage"),
            created_at=response_data["created_at"]
        )

        
        db.session.add(new_request)
        db.session.commit()

   return jsonify(response.json()), response.status_code
   
@app.route('/callback-url', methods=["POST"])
def callback_url():
    data = request.get_json()

    found_request = Request.query.filter_by(CheckoutRequestID=data["Body"]["stkCallback"]["CheckoutRequestID"]).first()
    
    new_transaction = Transaction(
        Request_id = found_request.id,
        MerchantRequestID = data["Body"]["stkCallback"]["MerchantRequestID"],
        CheckoutRequestID = data["Body"]["stkCallback"]["CheckoutRequestID"],
        ResultCode = data["Body"]["stkCallback"]["ResultCode"],
        ResultDesc = data["Body"]["stkCallback"]["ResultDesc"],
        created_at = datetime.now()
    )

    db.session.add(new_transaction)

    if data["Body"]["stkCallback"]["ResultCode"] == 0:
        transaction = Transaction.query.filter_by(CheckoutRequestID=data["Body"]["stkCallback"]["CheckoutRequestID"]).first()

        callback_data =  data["Body"]["stkCallback"]["CallbackMetadata"]["Item"]

        new_callback_metadata = CallbackMetadatum(
            transaction_id = transaction.id,
            Amount = callback_data[0]["Value"],
            MpesaReceiptNumber = callback_data[1]["Value"],
            TransactionDate = callback_data[2]["Value"],
            PhoneNumber = callback_data[3]["Value"],
            created_at = datetime.now()
        )
        
        db.session.add(new_callback_metadata)

    db.session.commit()
   
    return jsonify(data), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)