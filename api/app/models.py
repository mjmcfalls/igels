from app import bp
from app.igels_class import Igel
from flask import make_response
from flask import jsonify
from app.errors import bad_request
from flask import request
from flask_api import status
from werkzeug.utils import secure_filename
from wand.image import Image
from skimage.metrics import structural_similarity as ssim
import os
import numpy as np
import cv2
import os
import json
import time
import tempfile
import logging
import sys, getopt
# from dotenv import load_dotenv

envFile = '/app/env/env.json'
ALLOWED_EXTENSIONS = set(['xwd'])
ALLOWED_EXTENSIONS_REPORT = set(['json'])
logging.basicConfig( level=logging.INFO, handlers=[logging.StreamHandler()],format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
# load_dotenv(dotenv_path=envFile, verbose=True)
configData = None
with open(envFile, "r") as read_file:
    configData = json.load(read_file)

def allowed_file(filename, ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ext

def get_opencv_img_from_buffer(buffer, flags):
    bytes_as_np_array = np.frombuffer(buffer.read(), dtype=np.uint8)
    return cv2.imdecode(bytes_as_np_array, flags)

def compareFiles(targetImgLoc, baseImgLoc, hostname, dir, height, width):
    # logging.debug("running comparefile")
    # results = {}
    dim = (width, height)
    # logging.debug("Read in comparison img")
    targetImg = cv2.imread(baseImgLoc)
    targetImg = cv2.resize(targetImg, dim)
    targetImg = cv2.cvtColor(targetImg, cv2.COLOR_BGR2GRAY)

    newfile = os.path.join(dir, "{}.jpg".format(hostname))

    try:
        with Image(filename=targetImgLoc) as img: 
            img.format = 'jpeg'
            if img.size[0] == 3840:
                with img[0:1920, :] as cropped:
                    cropped.save(filename=newfile)
            else:
                img.save(filename=newfile)
        testImg = cv2.imread(newfile) 
        testImg = cv2.resize(testImg, dim)
        testImg = cv2.cvtColor(testImg, cv2.COLOR_BGR2GRAY)

        match = (ssim(targetImg, testImg) * 100)
        return round(match, 2), newfile

    except Exception as e:
        # logging.debug(e)
        logging.info("Manually check: ".format(hostname))
        results = "Manually Check - {}".format(hostname)
        return results

def igelReportMain(data):
    sender_email = configData['sender_email']
    receiver_email = configData['receiver_email']
    smtpserver = configData['smtpserver']
    remediationpercent = int(configData['remediationpercent'])
    brokenpercent = int(configData['brokenpercent'])
    db = configData['db']
    dailyFrozenDb = configData['dailyFrozenDb']
    # userHash = configData['userHash']
    umsBaseUri = configData['umsBaseUri']
    error_email  = configData['error_email']
    prod = configData['prod']
    # if os.getenv('prod') == "False":
        
    # else:
    # igel = Igel(userHash=userHash, umsBaseUri=umsBaseUri, sender_email=sender_email, receiver_email=receiver_email, smtpserver=smtpserver, remediationpercent=remediationpercent, brokenpercent=brokenpercent, db=db, dailyFrozenDb=dailyFrozenDb)
    igel = Igel(umsBaseUri=umsBaseUri, sender_email=sender_email, receiver_email=receiver_email, error_email=error_email, smtpserver=smtpserver, remediationpercent=remediationpercent, brokenpercent=brokenpercent, db=db, dailyFrozenDb=dailyFrozenDb, prod=prod)
    results = igel.processIgelRounding(data)
    del(igel)
    return results 

@bp.route("/v1/igel/report", methods=["POST"])
def processReport():
    if request.method == "POST":
        # check if the post request has the file part
        if "file" not in request.files:
            return make_response(jsonify({"error": "No File Sent"}), 400)

        file = request.files["file"]
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == "":
            return redirect(request.url)

        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_REPORT):
            data = json.load(request.files['file'])
            results = igelReportMain(data)
            # del data
            return make_response(jsonify(results), 200)
    return make_response(jsonify({"Invalid parameters": "500"}), 500)

@bp.route("/v1/igel/compare", methods=["POST"])
def processImage():
    if request.method == "POST":
        validate = request.args.get('validate')
        # check if the post request has the file part
        if "file" not in request.files:
            return make_response(jsonify({"error": "No File Sent"}), 400)

        file = request.files["file"]
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == "":
            return redirect(request.url)

        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS):
            BASEIMAGELOC = configData['BASEIMAGELOC']
            WORKINGIMGLOC = configData['WORKINGIMGLOC']
            HEIGHT = int(configData['HEIGHT'])
            WIDTH = int(configData['WIDTH'])
            with tempfile.TemporaryDirectory() as tmpdir:
                filename = secure_filename(file.filename)
                hostname = filename.split("_")[0]

                file.save(os.path.join(tmpdir, filename))

                if(validate):
                    logging.debug("Validate block True")
                    match, jpgfile = compareFiles(targetImgLoc=os.path.join(tmpdir, filename), baseImgLoc=WORKINGIMGLOC, dir=tmpdir, hostname=hostname, height=HEIGHT, width=WIDTH)
                    results = {"validate": match}
                else:
                    match, jpgfile = compareFiles(targetImgLoc=os.path.join(tmpdir, filename), baseImgLoc=BASEIMAGELOC, dir=tmpdir, hostname=hostname, height=HEIGHT, width=WIDTH)
                    results = {"match": match}

            return make_response(jsonify(results), 200)
    return make_response(jsonify({"Invalid parameters": "500"}), 500)
