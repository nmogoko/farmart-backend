import uuid
from config import Config
from datetime import datetime
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import Notification, Request, db, Transaction, CallbackMetadatum, Cart, User, Animal, Order
from sqlalchemy.exc import IntegrityError
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

@app.route('/add-cart', methods=["POST"])
def add_cart():
    data = request.get_json()

    user_id = data.get('user_id')
    animal_id = data.get('animal_id')
    quantity = data.get('quantity')

    if not all([user_id, animal_id, quantity]):
        return jsonify({"error": "user_id, animal_id, and quantity are required fields."}), 400
    
    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than 0."}), 400
    
    # Check if user exists
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    # Check if animal exists and is available
    animal = Animal.query.filter_by(id=animal_id).first()
    if not animal or not animal.is_available:
        return jsonify({"error": "Animal not found or not available."}), 404

    # Check if the item is already in the cart
    cart_item = Cart.query.filter_by(user_id=user_id, animal_id=animal_id).first()
    if cart_item:
        cart_item.quantity += quantity
    else:
        # Add new item to the cart
        cart_item = Cart(user_id=user_id, animal_id=animal_id, quantity=quantity)
       
        # Commit changes to the database
    try:
        db.session.add(cart_item)
        db.session.commit()
    except IntegrityError: 
        db.session.rollback()
        return jsonify({"error": "Failed to add item to cart."}), 500

    return jsonify({"message": "Item added to cart successfully."}), 201


@app.route('/notifications/<int:farmer_id>', methods=['GET'])
def get_notifications(farmer_id):
    """Fetch all notifications for a specific farmer."""
    notifications = Notification.query.filter_by(recipient_id=farmer_id).all()
    return jsonify([
        {
            'id': notification.id,
            'order_id': notification.order_id,
            'message': notification.message,
            'status': notification.status,
            'created_at': notification.created_at
        } for notification in notifications
    ])




@app.route('/notifications/<int:notification_id>', methods=['PUT'])
def respond_to_notification(notification_id):
    """Accept or decline a notification."""
    data = request.json
    notification = Notification.query.filter_by(id=notification_id).first()
    if not notification:
        return jsonify({'error': 'Notification not found'}), 404

    try:
        response = data.get('response')
        if response not in ['accepted', 'declined']:
            return jsonify({'error': 'Invalid response'}), 400

        notification.status = response

        # Update order status based on farmer's response
        order = notification.order
        order.status = 'accepted' if response == 'accepted' else 'declined'

        db.session.commit()
        return jsonify({'message': f'Notification {response}!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(port=5000, debug=True)