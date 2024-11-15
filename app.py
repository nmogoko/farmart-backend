from config import Config
from datetime import datetime
from extensions import jwt
from flask import Flask, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, JWTManager
from flask_migrate import Migrate
from models import Request, db, Transaction, CallbackMetadatum, Cart, User, Animal, Role, UsersRole,FarmersProfile
from sqlalchemy.exc import IntegrityError
from utils import generate_token, generate_timestamp, generate_password
from werkzeug.security import generate_password_hash, check_password_hash

import requests

app = Flask(__name__)
config = Config()

# Access environment variables
app.config['SECRET_KEY'] = config.JWT_SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATION

jwt = JWTManager(app)
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

# Helper function for assigning roles
def assign_role(user_id, role_name, description):
    role = Role.query.filter_by(role_name=role_name).first()
    if not role:
        role = Role(role_name=role_name, description=description)
        db.session.add(role)
        db.session.commit()

    user_role = UsersRole(user_id=user_id, role_id=role.id, created_at=datetime.utcnow())
    db.session.add(user_role)
    db.session.commit()


# Farmer registration
@app.route('/farmer-sign-up', methods=['POST'])
def farmer_sign_up():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')

    if not email or not password or not username:
        return jsonify({"msg": "Email, username, and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(email=email, username=username, password_hash=hashed_password, is_verified=False)
    db.session.add(new_user)
    db.session.commit()  # Commit to generate new_user.id

    # Assign farmer role
    assign_role(new_user.id, 'farmer', 'Farmer with access to list and manage animals')

    # Create Farmer Profile
    farmer_profile = FarmersProfile(user_id=new_user.id, farm_name=data.get('farm_name'), location=data.get('location'))
    db.session.add(farmer_profile)
    db.session.commit()

    return jsonify({"msg": "Farmer account created successfully"}), 201


# Buyer Registration
@app.route('/buyer-sign-up', methods=['POST'])
def buyer_sign_up():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')

    if not email or not password or not username:
        return jsonify({"msg": "Email, username, and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(email=email, username=username, password_hash=hashed_password, is_verified=False)

    db.session.add(new_user)
    db.session.commit()  # Commit to generate new_user.id

    # Assign buyer role
    assign_role(new_user.id, 'buyer', 'Buyer with access to browse and purchase animals')

    return jsonify({"msg": "Buyer account created successfully"}), 201


# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Invalid email or password"}), 401

    user_data = {
        "id": user.id,
        "username": user.username
    }

    access_token = create_access_token(identity=user_data)
    refresh_token = create_refresh_token(identity=user_data)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200


# Protected User Route
@app.route('/user-profile', methods=['GET'])
@jwt_required()
def user_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    
    if user:
        return jsonify({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_verified": user.is_verified
        }), 200
    else:
        return jsonify({"msg": "User not found"}), 404


# Refresh Token
@app.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200

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

# Helper function for assigning roles
def assign_role(user_id, role_name, description):
    role = Role.query.filter_by(role_name=role_name).first()
    if not role:
        role = Role(role_name=role_name, description=description)
        db.session.add(role)
        db.session.commit()

    user_role = UsersRole(user_id=user_id, role_id=role.id, created_at=datetime.utcnow())
    db.session.add(user_role)
    db.session.commit()


# Farmer registration
@app.route('/farmer-sign-up', methods=['POST'])
def farmer_sign_up():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')

    if not email or not password or not username:
        return jsonify({"msg": "Email, username, and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(email=email, username=username, password_hash=hashed_password, is_verified=False)
    db.session.add(new_user)
    db.session.commit()  # Commit to generate new_user.id

    # Assign farmer role
    assign_role(new_user.id, 'farmer', 'Farmer with access to list and manage animals')

    # Create Farmer Profile
    farmer_profile = FarmersProfile(user_id=new_user.id, farm_name=data.get('farm_name'), location=data.get('location'))
    db.session.add(farmer_profile)
    db.session.commit()

    return jsonify({"msg": "Farmer account created successfully"}), 201


# Buyer Registration
@app.route('/buyer-sign-up', methods=['POST'])
def buyer_sign_up():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')

    if not email or not password or not username:
        return jsonify({"msg": "Email, username, and password are required"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(email=email, username=username, password_hash=hashed_password, is_verified=False)

    db.session.add(new_user)
    db.session.commit()  # Commit to generate new_user.id

    # Assign buyer role
    assign_role(new_user.id, 'buyer', 'Buyer with access to browse and purchase animals')

    return jsonify({"msg": "Buyer account created successfully"}), 201


# Login Route
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Invalid email or password"}), 401

    user_data = {
        "id": user.id,
        "username": user.username
    }

    access_token = create_access_token(identity=user_data)
    refresh_token = create_refresh_token(identity=user_data)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200


# Protected User Route
@app.route('/user-profile', methods=['GET'])
@jwt_required()
def user_profile():
    current_user = get_jwt_identity()
    user = User.query.get(current_user['id'])
    
    if user:
        return jsonify({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_verified": user.is_verified
        }), 200
    else:
        return jsonify({"msg": "User not found"}), 404


# Refresh Token
@app.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200


if __name__ == '__main__':
    app.run(port=5000, debug=True)
