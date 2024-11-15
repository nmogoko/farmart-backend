from config import Config
from datetime import datetime
from flask import Flask, request, jsonify
from flask_migrate import Migrate
from models import Request, db, Transaction, CallbackMetadatum, Cart, User, Animal
from sqlalchemy.exc import IntegrityError
from utils import generate_token, generate_timestamp, generate_password
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

import requests

app = Flask(__name__)
config = Config()

# Access environment variables
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATION

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
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

# Route to add a new animal listing
@app.route('/animals', methods=['POST'])
def add_animal():
    data = request.get_json()

    # Check required fields
    missing_fields = [field for field in ['type_id', 'breed_id', 'age', 'price', 'farmer_id'] if field not in data]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing_fields)}"
        }), 400

    # Create a new Animal object
    new_animal = Animal(
        id=data['id'],
        farmer_id=data['farmer_id'],
        type_id=data['type_id'],
        breed_id=data['breed_id'],
        age=data['age'],
        price=data['price'],
        description=data.get('description', ''),
        is_available=True  # Assuming new listings are available by default
    )

    # Add and commit to the database
    try:
        db.session.add(new_animal)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Animal added successfully",
            "animal": new_animal
        }), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": f"An error occurred while adding the animal: {str(e)}"
        }), 500

# Route to update an existing animal listing
@app.route('/animals/<int:animal_id>', methods=['PUT'])
def update_animal(animal_id):
    data = request.get_json()

    # Find the animal by ID
    animal = Animal.query.get(animal_id)
    if animal is None:
        return jsonify({'message': 'Animal not found'}), 404

    # Update fields if present in the request
    if 'type_id' in data:
        animal.type_id = data['type_id']
    if 'breed_id' in data:
        animal.breed_id = data['breed_id']
    if 'age' in data:
        animal.age = data['age']
    if 'price' in data:
        animal.price = data['price']
    if 'description' in data:
        animal.description = data['description']
    if 'is_available' in data:
        animal.is_available = data['is_available']

    # Commit changes
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Animal listing updated successfully'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f"An error occurred while updating the animal: {str(e)}"}), 500

# Route to delete an animal listing
@app.route('/animals/<int:animal_id>', methods=['DELETE'])
def delete_animal(animal_id):

    animal = Animal.query.get(animal_id)
    if animal is None:
        return jsonify({'message': 'Animal not found'}), 404

    try:
        # Use merge to re-attach the animal object to the current session
        animal = db.session.merge(animal)
        db.session.delete(animal)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Animal listing deleted successfully'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': f"An error occurred while deleting the animal: {str(e)}"}), 500

# Route to get all animal listings
@app.route('/animals', methods=['GET'])
def get_animals():
    animals = Animal.query.all()
    animal_list = [
        {
            'id': animal.id,
            'farmer_id': animal.farmer_id,
            'type': animal.type.name if animal.type else None,
            'breed': animal.breed.name if animal.breed else None,
            'age': animal.age,
            'price': str(animal.price),
            'description': animal.description,
            'is_available': animal.is_available
        }
        for animal in animals
    ]
    return jsonify(animal_list), 200
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

if __name__ == '__main__':
    app.run(port=5000, debug=True)