from email.mime.multipart import MIMEMultipart
from email import encoders
from email.message import Message
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
import os
import json
import time
import tempfile
import mimetypes
import pendulum
import smtplib
import requests
import urllib3
import logging
import sys, getopt, copy
# from dotenv import load_dotenv

class Igel:
    umsParams = {
        "loginStub": "/umsapi/v3/login",
        "logoutStub": "/umsapi/v3/logout",
        "directoriesStub": "/umsapi/v3/directories/tcdirectories?facets=children",
        "detailsStub": "/umsapi/v3/thinclients?facets=details",
        "tcStub": "/umsapi/v3/thinclients",
        "statusStub":"/umsapi/v3/serverstatus",
        "headers": {"Authorization": "Basic c3ZjX3NhZGV2dG9vbHNAbXNqLm9yZzpWVnhlQ05iMXN2eEI3QjhLJTZKKi9SdV8vR3BwLj5FaQ=="},
    }
    
    prod = True
    umsBaseUri = None
    igelList = {'stats':{'total_igels':0, "unreachable":0, "frozen": 0, "remediated": 0, "attemptedremediated": 0, "RemovedFromService":0}, 'igels':{}}
    timestamp = pendulum.now('America/New_York')
    sender_email = "Mission Health Report Bot <msjreportbot@msj.org>"
    receiver_email = None
    error_email = None
    smtpserver = None
    remediationpercent = 90
    brokenpercent = 97
    db = None
    dailyFrozenDb = None
    strFormat = "%m-%d-%Y"
    htmlfile = "/app/src/test_html.html"
    removedFromService = "351472"
    errSubject = None

    def __init__(self, **kwargs):
        logging.basicConfig( level=logging.INFO, handlers=[logging.StreamHandler()],format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",)
        
        for key, value in kwargs.items():
            if 'receiver_email' == key:
                self.receiver_email = value
            elif 'sender_email' == key:
                self.sender_email = value
            elif 'remediationpercent' == key:
                self.remediationpercent = value
            elif 'brokenpercent' == key:
                self.brokenpercent = value 
            elif 'smtpserver' == key:
                self.smtpserver = value
            elif 'dailyFrozenDb' == key:
                self.dailyFrozenDb = value 
            elif 'db' == key:
                self.db = value
            elif 'umsBaseUri' == key:
                self.umsBaseUri = value
            elif 'error_email' == key:
                self.error_email = value
            # elif 'userHash' == key:
            #     self.umsParams['headers']['Authorization'] = self.umsParams['headers']['Authorization'] + value
            elif 'prod' == key:
                if value == "True":
                    self.prod = True
                else:
                    self.prod = False
        logging.info("Prod: {}".format(self.prod))
        # logging.info(kwargs)
        
        # logging.info(self.umsParams['headers'])
    def resetIgelList(self):
        self.igelList = {'stats':{'total_igels':0, "unreachable":0, "frozen": 0, "remediated": 0, "attemptedremediated": 0, "RemovedFromService":0}, 'igels':{}}

    def getRepeatOffenders(self, data, db):
        if os.path.isfile(db):
            with open(db, 'r') as ifile:
                dbData = json.load(ifile)
                # logging.info("open existing file")
        else:
            dbData = {}
            # logging.info("no file exists")
        # logging.info(dbData)
        currentWeek = str(self.timestamp.week_of_year)
        # logging.info("{} -- Week: {}".format(timestamp, currentWeek))
        if str(currentWeek) in dbData:
            logging.info("currentweek exists")
        else:
            dbData[currentWeek] = {}
    
        for item in data['igels']:
            # logging.info("item: {}".format(item))
            if 'broken_percent' in data['igels'][item]:
                if data['igels'][item]['broken_percent'] >= self.brokenpercent:
                    # logging.info("getRepeatOffenders frozen igel: {}".format(item))
                    if item in dbData[currentWeek]:
                        # if 'repeater'
                        dbData[currentWeek][item]['repeatOffender'] = dbData[currentWeek][item]['repeatOffender'] + 1
                    else: 
                        dbData[currentWeek][item] = { 'repeatOffender': 0, 'repeatUnreachable': 0}
                        dbData[currentWeek][item]['repeatOffender'] = 1 
                    # logging.info("{} - {}".format(item, dbData[currentWeek][item]))
                    data['igels'][item]['repeatOffender'] = dbData[currentWeek][item]['repeatOffender']
                    logging.debug("{} - {}".format(item, data['igels'][item]))

            if 'unreachable' in data['igels'][item]:
                if data['igels'][item]['unreachable'] == 1:
                    # logging.info("getRepeatOffenders unreachable: {}".format(item))
                    if item in dbData[currentWeek]:
                        dbData[currentWeek][item]['repeatUnreachable'] = dbData[currentWeek][item]['repeatUnreachable'] + 1
                    else:
                        dbData[currentWeek][item] = { 'repeatOffender': 0, 'repeatUnreachable': 0}
                        dbData[currentWeek][item]['repeatUnreachable'] = 1 
                        # logging.info("Add: {} - {}".format(item,dbData[currentWeek][item]))

            if item in dbData[currentWeek]:
                # logging.info("Updating: {}".format(item))
                data['igels'][item].update(dbData[currentWeek][item])
            else:
                # logging.info("Adding: {}".format(item))
                data['igels'][item].update({ 'repeatOffender': 0, 'repeatUnreachable': 0})

        # logging.info(dbData)
        with open(db, 'w') as ofile:
            json.dump(dbData, ofile)
        
        return data

    def saveDailyFrozen(self, data, db):
        unreachableList = []

        if os.path.isfile(db):
            with open(db, "r") as ifile:
                dbData = json.load(ifile)

        else:
            dbData = {}

        currentDate = str(self.timestamp.strftime("%Y%m%d"))

        if currentDate in dbData:
            logging.info("currentDate - {} - exists".format(currentDate))
        else:
            logging.info("currentDate - {} - !exists".format(currentDate))
            dbData[currentDate] = {"frozen": [], "unreachable": []}
        # logging.info(dbData)
        temp = []
        if data["stats"]["frozen"] > 0:
            logging.debug("Stats-frozen > 0")
            for k, v in data["igels"].items():
                logging.debug("{}, {}".format(k,v))
                if "broken_percent" in v:
                    if v["broken_percent"] >= self.brokenpercent:
                        temp.append(k.split(".")[0])
        else:
            logging.debug("Stats-frozen = 0")
            pass
        dbData[currentDate]['frozen'] = dbData[currentDate]['frozen'] + temp

        
        if any(v["repeatOffender"] > 1 for k, v in data["igels"].items()):
            for k, v in data["igels"].items():
                if v["repeatOffender"] > 1:
                    if  k.split(".")[0] in dbData[currentDate]['unreachable']:
                        pass
                    else:
                        unreachableList.append(k.split(".")[0])
        dbData[currentDate]['unreachable'] = dbData[currentDate]['unreachable'] + unreachableList
        
        with open(db, "w") as ofile:
            json.dump(dbData, ofile)
        # logging.info(data)
        return data

    def getFolder(self, id, folders):
        for dirs in folders:
            # logging.info(dirs)
            if dirs['parentID'] == id:
                # logging.info(dirs['name'])
                return getFolder(dirs['id'], folders)

    def searchBranch(self, branch, base):
        name = []
        if branch['id'] != "-1":
            parent = [ item for item in base if item['id'] == branch['parentID']]
            if len(parent) > 0:
                name = self.searchBranch(parent[0], base)
                name.append(branch['name'])
            else:
                name = [branch['name']]
        else:
            name = [branch['name']]
        return name

    def getIgelLocation(self, umsParams):
        requests.packages.urllib3.disable_warnings()
        requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
        try:
            requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += (
                ":HIGH:!DH:!aNULL"
            )
        except AttributeError:
            # no pyopenssl support used / needed / available
            pass
        
        status = requests.get("{}{}".format(self.umsBaseUri, umsParams['statusStub']), verify=False)
        if status.status_code == 200:
            logging.info("Ums reachable")
            with requests.Session() as session:
                logging.info("Logging into UMS")
                post = session.post("{}{}".format(self.umsBaseUri, umsParams['loginStub']), headers=umsParams['headers'], verify=False, stream=False)
                logging.info("Login results: {}".format(post.status_code))
                try:
                    logging.debug("Get UMS folders - {}{}".format(self.umsBaseUri, umsParams['directoriesStub']))
                    directoryResults = session.get("{}{}".format(self.umsBaseUri, umsParams['directoriesStub']), verify=False, stream=False)
                except Exception as e:
                    # logging.info("Error: unable to send email")
                    logging.info("Exception: {}".format(e))
                    results = {"Internal Server Error": 500}
                logging.info("Directory results: {}".format(directoryResults.status_code))
                if directoryResults.status_code == 200:
                    igelDirectories = directoryResults.json()
                    # logging.info(igelDirectories)
                    igelsResults = session.get("{}{}".format(self.umsBaseUri, umsParams['tcStub']), verify=False, stream=False)
                    # igelsLogout = igelsResults.content
                    igels = igelsResults.json()

                else:
                    # logoutResults = session.post("{}{}".format(self.umsBaseUri, umsParams['logoutStub']), verify=False)
                    # logoutContent = logoutResults.content
                    # logging.info("logging out of UMS - {}".format(logoutResults.status_code))
                    # session.close()
                    return {"UMS Error": directoryResults.status_code }
                
                # logoutResults = session.post("{}{}".format(self.umsBaseUri, umsParams['logoutStub']), verify=False)
                # logoutContent = logoutResults.content
                # logging.info("logging out of UMS - {}".format(logoutResults.status_code))
                # session.close()
            # requests.session().close()

            branchBottoms = []
            folderNames = {}
            for item in igelDirectories:
                branchBottoms.append(item)
            
            names = {}
            topLevel = ['Production', "QA", "Testing"]
            for branch in branchBottoms:
                names[branch['id']] = self.searchBranch(branch, igelDirectories)
                names[branch['id']] = [ x for x in names[branch['id']] if x not in topLevel ]

            for igel in igels:
                if igel['parentID'] in names:
                    igel['location'] = names[igel['parentID']]
            return igels
        else:
            return []

    def addLocation(self, igelList, umsData):
        for igel in igelList['igels']:
            igelList['igels'][igel]['location'] = [ "/".join(item['location']) for item in umsData if item['name'] == igel.split(".")[0] and 'location' in item]
        return igelList

    def generateReport(self, igels, timestamp): 
        logging.debug("generateReport")
        tableRows = []
        repeatRows = []
        unreachableRows = []
        subject = "[REPORT] - iGel Rounding Report -- {}".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"))
        footer = "<br/><br/><p><sup>1</sup>Based on data from {} through {}.<br/><sup>2</sup>Frozen detection threshold: {}%<br/><sup>3</sup>Validation detection threshold: {}%</p><br/>".format(timestamp.start_of('week').strftime(self.strFormat), timestamp.end_of('week').strftime(self.strFormat), self.brokenpercent, self.remediationpercent)
        header = "<p><h3>iGel Rounding Report from {} (Week {})</h3></p><hr>".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"), timestamp.week_of_year)
        repeatHeader =  "<br/><br/><b>Frozen Multiple Times<sup>1</sup></b>"
        remediatedHeader = "<br/><br/><b>Determined Frozen</b>"
        unreachableHeader = "<br/><br/><b>Unreachable by Tool<sup>1</sup></b>"
        logging.debug(igels)
        if igels["stats"]["frozen"] > 0:
            for k, v in igels["igels"].items():
                if "broken_percent" in v:
                    if v["broken_percent"] >= self.brokenpercent:
                        logging.info(k,v)
                        if "verified_percent" in v:
                            tableRows.append(
                                "<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["broken_percent"], v["verified_percent"]))
                        else:
                            tableRows.append(
                                "<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["broken_percent"], ""))

            table = "<table><tr><th>iGel</th><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><th>Location</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Frozen likelihood<sup>2</sup></th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Validation likelihood<sup>3</sup></th></tr>{}</table>".format(
                "".join(tableRows)
            )
        else:
            table = "<p>No Frozen iGels detected.</p>"

        stats = """<table>
        <tr><td>Total Igels from UMS:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr><td># in Removed From Service:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr><td>Unreachable:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr><td>Frozen:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr><td>Attempted Remediation:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr><td>Remediated:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
        <tr></table>""".format(
            igels["stats"]["total_igels"],
            igels["stats"]["RemovedFromService"],
            igels["stats"]["unreachable"],
            igels["stats"]["frozen"],
            igels["stats"]["attemptedremediated"],
            igels["stats"]["remediated"],
            )

        # Build table of repeat offenders
        if any(v["repeatOffender"] > 1 for k, v in igels["igels"].items()):
            for k, v in igels["igels"].items():
                if v["repeatOffender"] > 1:
                    repeatRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["repeatOffender"]))

            repeatTable = "<table><tr><th>iGel</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Location</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Times Frozen</th><tr>{}</table>".format("".join(repeatRows))
        else:
            repeatTable = "<p>No devices seen more than once.</p>"

        # Build table of unreachable devices
        if any(v["unreachable"] > 0 for k, v in igels["igels"].items()):
            for k, v in igels["igels"].items():
                if v["unreachable"] > 0:
                    logging.info(k,v) #align='center'
                    if len(v['location']) > 0:
                        unreachableRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td></tr>".format(k.split(".")[0], v['location'][0], v['repeatUnreachable']))
                    # else:
                        # unreachableRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td align='center'>{}</td></tr>".format(k.split(".")[0], "&nbsp;", v['repeatUnreachable']))
            unreachableTable = "<br/><table><tr><th>iGel</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Location</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Times Unreachable</th></tr>{}</table>".format("".join(unreachableRows))
        else:
            unreachableTable = "<p>No devices were unreachable.</p>"

        message = header + stats + remediatedHeader + table + repeatHeader + repeatTable + unreachableHeader + unreachableTable + footer
        return message

    def sendemail(self, message, timestamp, subject, sender_email, receiver_email):
        logging.info("sendemail")
        logging.info(type(receiver_email))
        if self.prod:
            # Build email message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(receiver_email)
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'html'))

            try:
                # Attempt to send email for prod
                smtpObj = smtplib.SMTP(self.smtpserver)
                # logging.info("Recipients header: {}".format(msg))
                # smtpObj.sendmail(self.sender_email, receiver_email, msg.as_string())
                smtpObj.send_message(msg)
                # logging.info("{}".format(msg))
                logging.info("Successfully sent email")
                results =  {"Success": 200}
            except Exception as e:
                # logging.info("Error: unable to send email")
                logging.info("Exception: {}".format(e))
                results = {"Internal Server Error": 500}
        else:    
            # Write htmlfile for test/dev
            logging.info("Write test/dev html report.")
            with open(self.htmlfile, "w") as ofile:
                ofile.write(message)
            results =  {"Success": 200}
        return results

    def getMetrics(self, data, umsData, igelList):
        logging.debug("GetMetrics")
        try:
            for item in data["stats"]:
                if item not in igelList["igels"]:
                    # logging.info(item)
                    if data["stats"][item]["unreachable"]:
                        igelList["stats"]["unreachable"] = igelList["stats"]["unreachable"] + 1
                    igelList["igels"][item] = {
                        "unreachable": data["stats"][item]["unreachable"]
                    }

            igelList["stats"]["total_igels"] = len(data["stats"])

            # Logic to pull specific data
            for plays in data["plays"]:
                for task in plays["tasks"]:
                    if ("Set verify_match fact" == task["task"]["name"] or "Set broken_match fact" == task["task"]["name"]):
                        # logging.info(task['task']['name'])
                        for host in task["hosts"]:
                            # logging.info(host)
                            # logging.info(task['hosts'][host])
                            if "ansible_facts" in task["hosts"][host]:
                                if "verify_match" in task["hosts"][host]["ansible_facts"]:
                                    # logging.info("verify_match - host: {}; verify percent: {}".format(host,task["hosts"][host]["ansible_facts"]["verify_match"]["validate"],))
                                    igelList["igels"][host]["verified_percent"] = task["hosts"][host]["ansible_facts"]["verify_match"]["validate"]

                                    if igelList["igels"][host]["verified_percent"] > self.remediationpercent:
                                        igelList["stats"]["remediated"] = igelList["stats"]["remediated"] + 1
                                if "broken_match" in task["hosts"][host]["ansible_facts"]:
                                    
                                    if task["hosts"][host]["ansible_facts"]["broken_match"]["match"] >= self.brokenpercent:
                                        logging.debug("broken_match - host: {}; broken percent: {}".format(host,task["hosts"][host]["ansible_facts"]["broken_match"]["match"],))
                                        igelList["stats"]["frozen"] = igelList["stats"]["frozen"] + 1
                                        igelList["stats"]["attemptedremediated"] = igelList["stats"]["attemptedremediated"] + 1
                                    igelList["igels"][host]["broken_percent"] = task["hosts"][host]["ansible_facts"]["broken_match"]["match"]
            # logging.info(igelList['igels'])

            # Get Number of devices in Removed From Service
            removalList = []
            # logging.info("Pre-removal length: {}".format(len(igelList['igels'])))
            for item in umsData:
                if 'parentID' in item:
                    if item['parentID'] == self.removedFromService:
                        # logging.info("Removal Item: {}".format(item['name']))
                        if "{}.msj.org".format(item['name']) in igelList['igels']:
                            # logging.info("Exists: {}".format(item['name']))
                            del igelList['igels']["{}.msj.org".format(item['name'])]

                        igelList["stats"]["RemovedFromService"] = igelList["stats"]["RemovedFromService"] + 1
            
            
            # logging.info("Post-removal length: {}".format(len(igelList['igels'])))
            logging.info("Stats: {}".format(igelList["stats"]))
            logging.debug("preGetRepeatOffenders: {}".format(igelList["stats"]))
            igelListUpdate = self.getRepeatOffenders(igelList, self.db)
            logging.debug("saveDailyFrozen: {}".format(igelListUpdate["stats"]))
            self.saveDailyFrozen(igelListUpdate, self.dailyFrozenDb)
            logging.debug("addLocation: {}".format(igelListUpdate["stats"]))
            results = self.addLocation(igelListUpdate, umsData)

        except Exception as e:
            logging.info("Exception: {}".format(e))
            logging.info(e)
            self.errorNotify(message="Exception: {}".format(e), subject=self.errSubject) 
            results = {"Internal Server Error": 500}
            logging.info(results)
        return results
    
    def errorNotify(self, message, subject):
        self.sendemail(timestamp=self.timestamp, message=message, subject=subject, sender_email=self.sender_email, receiver_email=self.error_email)

    def processIgelRounding(self, data):
        logging.info("processIgelRounding")
        self.resetIgelList()
        timestamp = pendulum.now('America/New_York') 
        self.timestamp = copy.copy(timestamp)
        subject = "[REPORT] - IGel Rounding Report from {}".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"))
        self.errSubject = "[REPORT] - ERROR - IGel Rounding Report from {}".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"))
        if len(data['stats'].keys()) == 0:
            message = "No data passed for processing!"
            self.errorNotify(message=message, subject=self.errSubject)
            return {"Error - No Data provided": 400}
        else:
            umsData = self.getIgelLocation(umsParams=self.umsParams)
            if "UMS Error" in umsData:
                self.errorNotify(message=umsData, subject=self.errSubject)                
                return umsData
            else:
                logging.debug("ProcessingIgelRounding self.igelList: {}".format(self.igelList["stats"]))
                igels = self.getMetrics(data=data, umsData=umsData, igelList=self.igelList)
                message = self.generateReport(igels=igels, timestamp=timestamp)
                results = self.sendemail(timestamp=self.timestamp, message=message, subject=subject, sender_email=self.sender_email, receiver_email=self.receiver_email)
                logging.info("Stats: {}".format(igels["stats"]))
            
            return results 


def main(argv):
    try:
        opts, args = getopt.getopt(argv, "h", ["file=", "umsuri="])
        # logging.info(opts)
    except getopt.GetoptError:
        logging.info("file.py --apikey <apikey> --apitoken <apitoken> --board <boardname>")
        sys.exit(2)

    for opt, arg in opts:
        # logging.info(opt)
        if opt == "-h":
            logging.info("test.py --apikey <apikey> --apitoken <apitoken> --board <boardname>")
            sys.exit()
        elif opt in ("-f", "--file"):
            # logging.info(opt,arg)
            datafile = arg

    load_dotenv(dotenv_path='/app/api/.env', verbose=True)
    sender_email = os.getenv('sender_email')
    receiver_email = os.getenv('receiver_email')
    smtpserver = os.getenv('smtpserver')
    remediationpercent = int(os.getenv('remediationpercent'))
    brokenpercent = int(os.getenv('brokenpercent'))
    db = os.getenv('db')
    dailyFrozenDb = os.getenv('dailyFrozenDb')
    userHash = os.getenv('userHash')
    umsBaseUri = os.getenv('umsBaseUri')

    if os.getenv('prod') == "False":
        igel = Igel(userHash=userHash, umsBaseUri=umsBaseUri, sender_email=sender_email, receiver_email=receiver_email, smtpserver=smtpserver, remediationpercent=remediationpercent, brokenpercent=brokenpercent, db=db, dailyFrozenDb=dailyFrozenDb, prod=False)
    else:
        igel = Igel(userHash=userHash, umsBaseUri=umsBaseUri, sender_email=sender_email, receiver_email=receiver_email, smtpserver=smtpserver, remediationpercent=remediationpercent, brokenpercent=brokenpercent, db=db, dailyFrozenDb=dailyFrozenDb)
    
    with open(datafile, "r") as ifile:
        data = json.load(ifile)
    igel.processIgelRounding(data)
        
if __name__ == "__main__":
    main(sys.argv[1:])

