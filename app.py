from flask import Flask, jsonify, request
from config import Config
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from flask_migrate import Migrate
from models import db, Animal, Order
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
config = Config()

# Access environment variables
# app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = config.SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = config.SQLALCHEMY_TRACK_MODIFICATIONS

# Initialize SQLAlchemy and Flask-Migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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
            "animal_id": new_animal.id
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

if __name__ == '__main__':
    app.run(port=5000, debug=True)