from flask import Flask
from flask import make_response
from flask import request
from flask import jsonify
from flask_cors import CORS
# from config import Config
import time
import os
import logging
# import numpy as np
# import cv2
# from skimage.metrics import structural_similarity as ssim
import os
# from wand.image import Image
import json
import time

class Config(object):
    DEBUG = True
    

def create_app(config_class=Config):
    application = Flask(__name__)
    CORS(application)

    from app import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    # application.run(debug=True, host="0.0.0.0", port=80)
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[logging.StreamHandler()])
    create_app()
    
    app.run(debug=True, host="0.0.0.0")
    # app.config.from_object()
