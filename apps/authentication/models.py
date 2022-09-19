# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import sys
import jwt
import json 
from functools import wraps
from decouple import config
from flask_login import UserMixin
from flask import g, request, redirect, url_for, render_template, flash, session
from apps import db, login_manager, elasticache_redis
from apps.authentication.util import hash_pass

class Users(db.Model, UserMixin):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True)
    email = db.Column(db.String(64), unique=True)
    password = db.Column(db.LargeBinary)
    is_admin = db.Column(db.Boolean, nullable=False)

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)

            setattr(self, property, value)        


    def __repr__(self):
        return str(self.username)

    def as_dict(self):
        return {c.name: getattr(self, c.name).decode('utf-8') if type(getattr(self,c.name)) is bytes else getattr(self,c.name) for c in self.__table__.columns}

    def to_json(self):
        print("Users dict: ",self.as_dict())        
        print("Users json: ",json.dumps(self.as_dict()))
        # print("Users json_indent4: ",json.dumps(self.as_dict(),indent=4))
        return json.dumps(self.as_dict())

# class Employees(db.Model):

#     __tablename__ = 'employees'

#     id = db.Column(db.Integer, primary_key=True)
#     username = db.Column(db.String(64), unique=True)
#     email = db.Column(db.String(64), unique=True)
#     age = db.Column(db.Integer)
#     username = db.Column(db.String(64), unique=True)
#     password = db.Column(db.LargeBinary)

#     def __init__(self, **kwargs):
#         for property, value in kwargs.items():
#             # depending on whether value is an iterable or not, we must
#             # unpack it's value (when **kwargs is request.form, some values
#             # will be a 1-element list)
#             if hasattr(value, '__iter__') and not isinstance(value, str):
#                 # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
#                 value = value[0]

#             if property == 'password':
#                 value = hash_pass(value)  # we need bytes here (not plain str)

#             setattr(self, property, value)

#     def __repr__(self):
#         return str(self.username)

class Employees(db.Model):

    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)    
    full_name = db.Column(db.String(64), unique=True)        
    contact = db.Column(db.Integer)
    address = db.Column(db.String(64), unique=True)
    # city = db.Column(db.String(64), unique=True)
    # country = db.Column(db.String(64), unique=True)
    # postal_code = db.Column(db.String(64), unique=True)
    department = db.Column(db.String(64), unique=True)
    job = db.Column(db.String(64), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0] 

            if property == 'password':
                value = hash_pass(value)  # we need bytes here (not plain str)           

            setattr(self, property, value)

    def __repr__(self):
        return str(self.username)

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Departments(db.Model):

    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)


    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]                        
            setattr(self, property, value)                
            

    def __repr__(self):
        return str(self.title)

class Jobs(db.Model):

    __tablename__ = 'jobs'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), unique=True)


    def __init__(self, **kwargs):
        for property, value in kwargs.items():
            # depending on whether value is an iterable or not, we must
            # unpack it's value (when **kwargs is request.form, some values
            # will be a 1-element list)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                # the ,= unpack of a singleton fails PEP8 (travis flake8 test)
                value = value[0]            

            setattr(self, property, value)

    def __repr__(self):
        return str(self.title)

    def as_dict(self):
       return {c.name: getattr(self, c.name) for c in self.__table__.columns}


@login_manager.user_loader
def user_loader(id):
    return Users.query.filter_by(id=id).first()


@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    user = Users.query.filter_by(username=username).first()
    return user if user else None


def token_required(func):
    @wraps(func)
    def decorator(*args, **kwargs):
        print(f'token_required decorator auth_token: {session.get("auth_token")}', file=sys.stdout)
        token = None
        # ensure the jwt-token is passed with the headers
        if not (session.get("auth_token") and elasticache_redis.get(session.get("auth_token"))):        
            return render_template('home/page-403.html'), 403                            
        token = session.get("auth_token")
        print(f'token: {token}', file=sys.stdout)
        data = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
        print(f'token decoded: {data}', file=sys.stdout)
        current_user = Users.query.filter_by(id=data['id']).first()                    
        # print(f'json user: {json.dumps(current_user)}', file=sys.stdout)         
        elasticache_redis.hset(token,"user",current_user.to_json())
        print(f'cache user: {elasticache_redis.hget(token,"user")}', file=sys.stdout)         
        # try:
        #     # decode the token to obtain user public_id
        #     print(f'token: {token}', file=sys.stdout)
        #     data = jwt.decode(token, config('SECRET_KEY'), algorithms=['HS256'])
        #     print(f'token decoded: {data}', file=sys.stdout)
        #     current_user = Users.query.filter_by(id=data['id']).first()
        # except:
        #     return render_template('home/page-403.html'), 403
         # Return the user information attached to the token
        return func(*args, **kwargs)
    return decorator