from flask import Flask
from flask import make_response
from flask import request
from flask import jsonify
from flask_cors import CORS
import time
import os
import logging


class Config(object):
    DEBUG = True

app = Flask(__name__)

cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
from app import bp as api_bp
app.register_blueprint(api_bp, url_prefix='/api')


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler()])
    app.run(debug=True, host="0.0.0.0", port=5001)
