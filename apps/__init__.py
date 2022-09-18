# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

import sys
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from importlib import import_module
from decouple import config
import boto3
from flask_session import Session
import redis

db = SQLAlchemy()
login_manager = LoginManager()
sess = Session()
aws_session = boto3.session.Session(aws_access_key_id=config("AWS_ACCESS_KEY"), aws_secret_access_key=config("AWS_SECRET_KEY"), aws_session_token=config("AWS_SESSION_TOKEN"))
s3_bucket = aws_session.resource('s3').Bucket(config('STORAGE_BUCKET')) if aws_session else ''
s3_bucket_location = aws_session.client('s3').get_bucket_location(Bucket=config('STORAGE_BUCKET'))['LocationConstraint'] if aws_session else ''
print(config("SESSION_REDIS"),file=sys.stdout)
# myredis = redis.Redis(host=config("REDIS_HOST"), port=6379, decode_responses=True)
# print(f'ping myredis: {myredis.ping()}', file=sys.stdout)
# myredis.set("hi","yoyooy")
# print(f'myredis hi: {myredis.get("hi")}', file=sys.stdout)
elasticache_redis = redis.Redis.from_url(f'redis://{config("SESSION_REDIS")}', decode_responses=True)
print(f'ping redis: {elasticache_redis.ping()}', file=sys.stdout)

def register_extensions(app):
    db.init_app(app)
    login_manager.init_app(app)
    sess.init_app(app)            


def register_blueprints(app):
    for module_name in ('authentication', 'home'):
        module = import_module('apps.{}.routes'.format(module_name))
        app.register_blueprint(module.blueprint)


def configure_database(app):

    @app.before_first_request
    def initialize_database():
        db.create_all()

    @app.teardown_request
    def shutdown_session(exception=None):
        db.session.remove()

def get_object_url(object_name):
    return f"https://s3{s3_bucket_location}.amazonaws.com/{config('STORAGE_BUCKET')}/{object_name}"

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    return app
