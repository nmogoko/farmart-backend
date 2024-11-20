from config import Config
from datetime import datetime
from flask import Flask, request, jsonify, g
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, JWTManager, decode_token, get_jwt
from flask_migrate import Migrate
from models import Request, db, Transaction, CallbackMetadatum, Cart, User, Animal, Role, UsersRole,FarmersProfile, Type, Notification, Breed
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from utils import generate_token, generate_timestamp, generate_password, with_user_middleware
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

blacklist = set()

@app.route('/initiate-payment', methods=['POST'])
@generate_token
@with_user_middleware
def initiate_payment():
   user_id = g.user_id  # Get the user ID from the middleware

   if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
   
   found_user = User.query.filter_by(id=user_id).first()

   if not found_user:
        return jsonify({"error": "Something wrong happened. Please try again later or contact support."}), 404
      
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
    "PartyA": found_user.phone_number,    
    "PartyB": config.MPESA_BUSINESS_SHORTCODE,   
    "PhoneNumber": found_user.phone_number,    
    "CallBackURL": "https://farmart-backend-f2uh.onrender.com/callback-url",  
    "AccountReference": data["orderId"],    
    "TransactionDesc": "Paying for items in farmart"
   }

   response = requests.post(request_url, json=payload, headers=headers)
 
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

        # Manually convert new_animal to a dictionary
        animal_dict = {
            "farmer_id": new_animal.farmer_id,
            "type_id": new_animal.type_id,
            "breed_id": new_animal.breed_id,
            "age": new_animal.age,
            "price": new_animal.price,
            "description": new_animal.description,
            "is_available": new_animal.is_available
        }

        return jsonify({
            "status": "success",
            "message": "Animal added successfully",
            "animal": animal_dict
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
    animal = db.session.get(Animal, animal_id)
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

    animal = db.session.get(Animal, animal_id)
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
   # Get query parameters for filtering
    animal_type = request.args.get('type', None)
    animal_breed = request.args.get('breed', None)

    query = Animal.query.join(Type).join(Breed)

    # Apply filters if provided
    if animal_type:
        query = query.filter(Type.name.ilike(f"%{animal_type}%"))
    if animal_breed:
        query = query.filter(Breed.name.ilike(f"%{animal_breed}%"))

    # Execute the query
    animals = query.all()

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

@app.route('/cart', methods=["POST"])
@with_user_middleware
def add_cart():
    if g.user_id is None:
        return jsonify({"error": "Unauthorized access"}), 401
    
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
    # db.session.commit()  # Commit to generate new_user.id

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

@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    return jwt_payload['jti'] in blacklist

# logout
@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt()['jti']  # JWT ID
    blacklist.add(jti)
    return jsonify(msg="Successfully logged out"), 200

# reset password
@app.route('/reset-password/<token>', methods=['POST'])
def reset_password(token):
    data = request.get_json()
    new_password = data.get('new_password')

    if not new_password:
        return jsonify({"msg": "New password is required"}), 400

    try:
        # Decode the token to get the user identity
        decoded_token = decode_token(token)
        email = decoded_token['sub']['email']
    except Exception as e:
        return jsonify({"msg": "Invalid token"}), 401
    
    hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')

    # Update the password in the database using SQLAlchemy
    user = User.query.filter_by(email=email).first()
    if user:
        user.password = hashed_password
        db.session.commit()
        return jsonify({"msg": "Password has been reset successfully"}), 200
    else:
        return jsonify({"msg": "User not found"}), 404


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


@app.route('/cart/<int:id>', methods=["GET"])
@with_user_middleware
def get_single_cart(id):
    if not id:
        return jsonify({"error": "cart_id missing."}), 400
    
    if g.user_id is None:
        return jsonify({"error": "Unauthorized access"}), 401
     
    cart_items = Cart.query.filter_by(id=id, user_id=g.user_id).all()

    if not cart_items:
        return jsonify({"message": "Cart is empty."}), 404

    payment_data = []
    total_amount = 0

    for item in cart_items:
        animal = Animal.query.filter_by(id=item.animal_id).first()
        if not animal:
            continue  # Skip if the animal doesn't exist

        type =Type.query.filter_by(id=animal.type_id).first()
        if not type:
            type = None 

        # Calculate the total price for the item
        item_total = animal.price * item.quantity
        total_amount += item_total

        # Add item details to the payment data
        payment_data.append({
            "animal_id": animal.id,
            "animal_name": type.name, 
            "price_per_item": animal.price,
            "quantity": item.quantity,
            "total_price": item_total
        })

    # Return the payment data and total amount
    return jsonify({
        "payment_data": payment_data,
        "total_amount": total_amount
    }), 200


@app.route('/cart/<int:id>', methods=["DELETE"])
@with_user_middleware
def clear_cart():
    if g.user_id is None:
        return jsonify({"error": "Unauthorized access"}), 401
    
    # Extract user_id from the request body or query parameters
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({"error": "user_id is required."}), 400

    try:
        # Delete all cart items for the given user_id
        Cart.query.filter_by(user_id=user_id).delete()

        # Commit the changes to the database
        db.session.commit()

        return jsonify({"message": "Cart cleared successfully."}), 200
    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"error": "Failed to clear cart.", "details": str(e)}), 500
    
@app.route('/cart/<int:id>', methods=["PATCH"])
def reduce_cart_item():
    # Extract user_id and animal_id from the request body
    data = request.get_json()
    user_id = data.get('user_id')
    animal_id = data.get('animal_id')

    if not user_id or not animal_id:
        return jsonify({"error": "user_id and animal_id are required."}), 400

    try:
        # Find the cart item to update
        cart_item = Cart.query.filter_by(user_id=user_id, animal_id=animal_id).first()

        if not cart_item:
            return jsonify({"error": "Item not found in cart."}), 404

        # Decrease the quantity by 1
        cart_item.quantity -= 1

        # If quantity is 0 or less, remove the item from the cart
        if cart_item.quantity <= 0:
            db.session.delete(cart_item)
        else:
            db.session.add(cart_item)  # Update the cart item if still valid

        # Commit the changes to the database
        db.session.commit()

        return jsonify({"message": "Item quantity reduced successfully."}), 200

    except Exception as e:
        db.session.rollback()  # Rollback in case of error
        return jsonify({"error": "Failed to update item quantity.", "details": str(e)}), 500

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
