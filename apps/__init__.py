import sys
from flask import Flask, g
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

# aws_session = boto3.session.Session(aws_access_key_id=config("AWS_ACCESS_KEY"), aws_secret_access_key=config("AWS_SECRET_KEY"), aws_session_token=config("AWS_SESSION_TOKEN"))
# s3_bucket = aws_session.resource('s3').Bucket(config('STORAGE_BUCKET'))
# s3_bucket_constraint = aws_session.client('s3').get_bucket_location(Bucket=config('STORAGE_BUCKET'))['LocationConstraint']
# print(f'my aws_session: {aws_session}',file=sys.stdout)
s3_client = boto3.client('s3')
s3_bucket = boto3.resource('s3').Bucket(config('STORAGE_BUCKET'))
s3_bucket_constraint = s3_client.get_bucket_location(Bucket=config('STORAGE_BUCKET'))['LocationConstraint']
s3_bucket_location = '-'+s3_bucket_constraint if s3_bucket_constraint else '' 
object_url = "https://s3{0}.amazonaws.com/{1}".format(
    s3_bucket_location,
    config("STORAGE_BUCKET")
)
print(f'my s3_bucket: {s3_bucket}',file=sys.stdout)
print(f'my s3_bucket_constraint: {s3_bucket_constraint}',file=sys.stdout)
print(f'my s3_bucket_location: {s3_bucket_location}',file=sys.stdout)

elasticache_redis = redis.Redis.from_url(f'redis://{config("SESSION_REDIS")}', decode_responses=True)
print(f'ping redis: {elasticache_redis.ping()}', file=sys.stdout)

# RUN LOCALLY
# aws_session = ""
# s3_client = ""
# s3_bucket = ""
# s3_bucket_constraint = ""
# s3_bucket_location = '-'+s3_bucket_constraint if s3_bucket_constraint else '' 
# object_url = "https://s3{0}.amazonaws.com/{1}".format(
#     s3_bucket_location,
#     config("STORAGE_BUCKET")
# )
# elasticache_redis = ''

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

    @app.context_processor
    def inject_CDN():        
        return {"cdn_link": config("CLOUDFRONT_LINK", default="") }

def create_app(config):
    app = Flask(__name__)
    app.config.from_object(config)
    register_extensions(app)
    register_blueprints(app)
    configure_database(app)
    return app
