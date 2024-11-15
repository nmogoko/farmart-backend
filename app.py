from flask import Flask, jsonify, request, abort
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate
from models import db, Role, Type, User, Breed, FarmersProfile, UsersRole, Animal, Cart, Order, Request, Transaction, CallbackMetadatum
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
config = Config()

# Access environment variables
app.config['SQLALCHEMY_DATABASE _URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_SECRET_KEY'] = config.SQLALCHEMY_SECRET_KEY
app.config['SQLALCHEMY_TRACK MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATION

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Route to add a new animal listing
@app.route('/animals', methods=['POST'])
def add_animal():
    data = request.get_json()

    # Check required fields
    if not data or 'type_id' not in data or 'breed_id' not in data or 'age' not in data or 'price' not in data or 'farmer_id' not in data:
        abort(400, description="Missing required fields")

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
        return jsonify({"message": "Animal added successfully", "animal_id": new_animal.id}), 201 
    except SQLAlchemyError as e:
        db.session.rollback()
        abort(500, description=str(e))

# Route to update an existing animal listing
@app.route('/animals/<int:animal_id>', methods=['PUT'])
def update_animal(animal_id):
    data = request.get_json()
    animal = Animal.query.get(animal_id)

    # Find the animal by ID
    animal = Animal.query.get(animal_id)
    if animal is None:
        return jsonify({'message': 'Animal not found'}), 404
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
        return jsonify({'message': 'Animal listing updated successfully'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        abort(500, description=str(e))

# Route to delete an animal listing
@app.route('/animals/<int:animal_id>', methods=['DELETE'])
def delete_animal(animal_id):
    animal = Animal.query.get(animal_id)

    animal = Animal.query.get(animal_id)
    if animal is None:
        return jsonify({'message': 'Animal not found'}), 404

    try:
        # Use merge to re-attach the animal object to the current session
        animal = db.session.merge(animal)
        db.session.delete(animal)
        db.session.commit()
        return jsonify({'message': 'Animal listing deleted successfully'}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        abort(500, description=str(e))

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

@app.route('/orders/<int:order_id>/farmer-action', methods=['POST'])
def farmer_action_on_order(order_id):
    # Get the order from the database
    order = Order.query.get(order_id)
    
    order = Order.query.get(order_id)
    if not order:
        abort(404, description="Order not found")
    
    # Ensure that only orders that are 'payment_success' can be confirmed or rejected
    if order.status != 'payment_success':
        abort(400, description="Order cannot be modified")

    # Get action from request data
    data = request.get_json()
    action = data.get('action')
    
    if action == 'confirm':
        order.status = 'farmer_confirmed'  
    elif action == 'reject':
        order.status = 'farmer_rejected'  
    else:
        abort(400, description="Invalid action. Action must be 'confirm' or 'reject'")

    try:
        db.session.commit()
        return jsonify(message=f"Order {action}d successfully by farmer."), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        abort(500, description="An error occurred while processing your request")

@app.route('/orders/<int:order_id>/buyer-action', methods=['POST'])
def buyer_action_on_order(order_id):
    # Get the order from the database
    order = Order.query.get(order_id)
    
    order = Order.query.get(order_id)
    if not order:
        abort(404, description="Order not found")
    
    # Ensure that only orders that are 'payment_success' can be confirmed or cancelled
    if order.status != 'payment_success':
        abort(400, description="Order cannot be modified")

    # Get action from request data
    data = request.get_json()
    action = data.get('action')
    
    if action == 'confirm':
        order.status = 'buyer_confirmed'  
    elif action == 'cancel':
        order.status = 'cancelled'  
    else:
        abort(400, description="Invalid action. Action must be 'confirm' or 'cancel'")

    try:
        db.session.commit()
        return jsonify(message=f"Order {action}d successfully by buyer."), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        abort(500, description="An error occurred while processing your request")


if __name__ == '__main__':
    app.run(port=5000, debug=True)