from flask import Blueprint

bp = Blueprint('api', __name__)

from app import models
from flask import Flask
from flask import make_response
from flask import request
from flask import jsonify
from flask_cors import CORS
# from config import Config
import time
import os
import logging

def create_app():
    app = Flask(__name__)
    CORS(app)
    from app import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api/')