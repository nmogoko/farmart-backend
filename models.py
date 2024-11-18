# coding: utf-8
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import relationship

db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'Roles'

    id = Column(Integer, primary_key=True)
    role_name = Column(String)
    description = Column(String)
    created_at = Column(DateTime)


class Type(db.Model):
    __tablename__ = 'Types'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class User(db.Model):
    __tablename__ = 'Users'

    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    password_hash = Column(String)
    phone_number = Column(BigInteger)
    is_verified = Column(Boolean)
    password_reset_token = Column(String)


class Breed(db.Model):
    __tablename__ = 'Breeds'

    id = Column(Integer, primary_key=True)
    type_id = Column(ForeignKey('Types.id'))
    name = Column(String)

    type = relationship('Type')


class FarmersProfile(db.Model):
    __tablename__ = 'FarmersProfile'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('Users.id'))
    farm_name = Column(String)
    location = Column(String)

    user = relationship('User')


class UsersRole(db.Model):
    __tablename__ = 'UsersRoles'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('Users.id'))
    role_id = Column(ForeignKey('Roles.id'))
    created_at = Column(DateTime)

    role = relationship('Role')
    user = relationship('User')


class Animal(db.Model):
    __tablename__ = 'Animals'

    id = Column(Integer, primary_key=True)
    farmer_id = Column(ForeignKey('FarmersProfile.id'))
    type_id = Column(ForeignKey('Types.id'))
    breed_id = Column(ForeignKey('Breeds.id'))
    age = Column(Integer)
    price = Column(Numeric)
    description = Column(Text)
    is_available = Column(Boolean)

    breed = relationship('Breed')
    farmer = relationship('FarmersProfile')
    type = relationship('Type')


class Cart(db.Model):
    __tablename__ = 'Cart'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('Users.id'))
    animal_id = Column(ForeignKey('Animals.id'))
    quantity = Column(Integer)

    animal = relationship('Animal')
    user = relationship('User')


class Order(db.Model):
    __tablename__ = 'Orders'

    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('Users.id'))
    animal_id = Column(ForeignKey('Animals.id'))
    order_id = Column(String, unique=True)
    quantity = Column(Integer)
    status = Column(Enum('initiated', 'payment_in_progress', 'payment_success', 'payment_failed', name='order_status'))
    created_at = Column(DateTime)

    animal = relationship('Animal')
    user = relationship('User')


class Request(db.Model):
    __tablename__ = 'Requests'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.ForeignKey('Orders.order_id'))
    user_id = db.Column(db.ForeignKey('Users.id'))
    MerchantRequestID = db.Column(db.String)
    CheckoutRequestID = db.Column(db.String)
    ResponseCode = db.Column(db.String)
    ResponseDescription = db.Column(db.String)
    CustomerMessage = db.Column(db.String)
    created_at = db.Column(db.DateTime)

    order = db.relationship('Order')
    user = db.relationship('User')


class Transaction(db.Model):
    __tablename__ = 'Transactions'

    id = Column(Integer, primary_key=True)
    Request_id = Column(ForeignKey('Requests.id'))
    MerchantRequestID = Column(String)
    CheckoutRequestID = Column(String)
    ResultCode = Column(String)
    ResultDesc = Column(String)
    created_at = Column(DateTime)

    Request = relationship('Request')


class CallbackMetadatum(db.Model):
    __tablename__ = 'CallbackMetadata'

    id = Column(Integer, primary_key=True)
    transaction_id = Column(ForeignKey('Transactions.id'))
    Amount = Column(Numeric(10, 2))
    MpesaReceiptNumber = Column(String)
    TransactionDate = Column(BigInteger)
    PhoneNumber = Column(BigInteger)
    created_at = Column(DateTime)

    transaction = relationship('Transaction')

class Notification(db.Model):
    __tablename__ = 'Notifications'

    id = Column(Integer, primary_key=True)
    sender_id = Column(ForeignKey('Users.id'))  # Buyer
    recipient_id = Column(ForeignKey('Users.id'))  # Farmer
    order_id = Column(ForeignKey('Orders.id'))
    message = Column(Text)
    status = Column(Enum('pending', 'accepted', 'declined', name='notification_status'), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

    sender = relationship('User', foreign_keys=[sender_id])
    recipient = relationship('User', foreign_keys=[recipient_id])
    order = relationship('Order')