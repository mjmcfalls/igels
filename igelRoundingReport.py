import json
import os
import requests
import urllib3
import sys, getopt
import json
# import mimetypes
# from email.mime.multipart import MIMEMultipart
# from email import encoders
# from email.message import Message
# from email.mime.audio import MIMEAudio
# from email.mime.base import MIMEBase
# from email.mime.image import MIMEImage
# from email.mime.text import MIMEText
import pendulum
import smtplib
from email.message import EmailMessage
from email.utils import make_msgid


umsParams = {
    "baseUri": "https://SERVER-ADDRESS:8443",
    "loginStub": "/umsapi/v3/login",
    "logoutStub": "/umsapi/v3/logout",
    "directoriesStub": "/umsapi/v3/directories/tcdirectories?facets=children",
    "detailsStub": "/umsapi/v3/thinclients?facets=details",
    "tcStub": "/umsapi/v3/thinclients",
    "statusStub":"/umsapi/v3/serverstatus",
    "headers": {"Authorization": "Basic BASE64-ENCODED-PASS"},
}

igelList = {"stats": {"total_igels": 0,"unreachable": 0,"frozen": 0,"remediated": 0,"attemptedremediated": 0,},"igels": {},}
timestamp = pendulum.now("America/New_York")

sender_email = "DISPLAY NAME <USER@EMAIL.COM>"
receiver_email = "RECEIVER-EMAIL"
smtpserver = 'SMTP-ADDRESS'
remediationpercent = 90
brokenpercent = 97
db = "/app/db/repeatOffenders.json"
dailyFrozenDb = "/app/db/dailyFrozenDevices.json"
htmlfile = "/app/src/test_html.html"
strFormat = "%m-%d-%Y"

def sendemail(timestamp, igels):
    tableRows = []
    repeatRows = []
    unreachableRows = []
    subject = "[REPORT] - iGel Rounding Report -- {}".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"))
    footer = "<br/><br/><p><sup>1</sup>Based on data from {} through {}.<br/><sup>2</sup>Frozen detection threshold: {}%<br/><sup>3</sup>Validation detection threshold: {}%</p><br/>".format(timestamp.start_of('week').strftime(strFormat), timestamp.end_of('week').strftime(strFormat), brokenpercent, remediationpercent)
    header = "<p><h3>iGel Rounding Report from {} (Week {})</h3></p><hr>".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"), timestamp.week_of_year)
    repeatHeader =  "<br/><br/><b>Frozen Multiple Times<sup>1</sup></b>"
    remediatedHeader = "<br/><br/><b>Determined Frozen</b>"
    unreachableHeader = "<br/><br/><b>Unreachable by Tool</b>"

    if igels["stats"]["frozen"] > 0:
        for k, v in igels["igels"].items():
            # print(k,v)
            if v["unreachable"] == 0:
                # print("unreachable == 0")
                # print(v['broken_percent'], v['verified_percent'])
                if "broken_percent" in v:
                    if v["broken_percent"] >= brokenpercent:
                        if "verified_percent" in v:
                            tableRows.append(
                                "<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["broken_percent"], v["verified_percent"]))
                        else:
                            tableRows.append(
                                "<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["broken_percent"], ""))
            #         else:
            #         tableRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k,"", ""))
            # else:
            #     tableRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k,"", ""))
        table = "<table><tr><th>iGel</th><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><th>Location</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Frozen likelihood<sup>2</sup></th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Validation likelihood<sup>3</sup></th></tr>{}</table>".format(
            "".join(tableRows)
        )
    else:
        table = "<p>No Frozen iGels detected.</p>"

    stats = """<table>
    <tr><td>Total Igels from UMS:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
    <tr><td>Unreachable:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
    <tr><td>Frozen:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
    <tr><td>Attempted Remediation:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
    <tr><td>Remediated:</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>
    <tr></table>""".format(
        igels["stats"]["total_igels"],
        igels["stats"]["unreachable"],
        igels["stats"]["frozen"],
        igels["stats"]["attemptedremediated"],
        igels["stats"]["remediated"],
        )

    # Build table of repeat offenders
    if any(v["repeatOffender"] > 1 for k, v in igels["igels"].items()):
        for k, v in igels["igels"].items():
            if v["repeatOffender"] > 1:
                repeatRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k.split(".")[0], v['location'][0], v["repeatOffender"]))

        repeatTable = "<table><tr><th>iGel</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Location</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Times Frozen</th><tr>{}</table>".format("".join(repeatRows))
    else:
        repeatTable = "<p>No devices seen more than once.</p>"

    # Build table of unreachable devices
    if any(v["unreachable"] > 0 for k, v in igels["igels"].items()):
        for k, v in igels["igels"].items():
            if v["unreachable"] > 0:
                # print(k,v)
                unreachableRows.append("<tr><td>{}</td><td>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td><td>{}</td></tr>".format(k.split(".")[0], v['location'][0]))
        unreachableTable = "<br/><table><tr><th>iGel</th><th>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</th><th>Location</th></tr>{}</table>".format("".join(unreachableRows))
    else:
        unreachableTable = "<p>No devices were unreachable.</p>"

    message = header + stats + remediatedHeader + table + repeatHeader + repeatTable + unreachableHeader + unreachableTable + footer

    # Build email message
    # msg = MIMEMultipart()
    msg = EmailMessage()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = "[REPORT] - IGel Rounding Report from {}".format(timestamp.strftime("%m-%d-%Y %H:%M:%S"))
    msg.set_content(message, subtype='html')
    # msg.attach(MIMEText(message, 'html'))

    # Attempt to send email
    # with open(htmlfile, "w") as ofile:
    #     ofile.write(message)
    try:
        smtpObj = smtplib.SMTP(smtpserver)
        # smtpObj.sendmail(sender_email, receiver_email, msg.as_string())
        print("Successfully sent email")
        results =  {"Success": 200}
    except Exception as e:
        # print("Error: unable to send email")
        print("Exception: {}".format(e))
        results = {"Internal Server Error": 500}

    return results


def repeatOffenders(data, db):
    if os.path.isfile(db):
        with open(db, "r") as ifile:
            dbData = json.load(ifile)
            # print("open existing file")
    else:
        dbData = {}
        # print("no file exists")
    # print(dbData)
    currentWeek = str(timestamp.week_of_year)
    # print("{} -- Week: {}".format(timestamp, currentWeek))
    if str(currentWeek) in dbData:
        print("currentweek exists")
    else:
        dbData[currentWeek] = {}

    for item in data["igels"]:
        if "broken_percent" in data["igels"][item]:
            if data["igels"][item]["broken_percent"] >= brokenpercent:
                # print(item)
                if item in dbData[currentWeek]:
                    dbData[currentWeek][item] = dbData[currentWeek][item] + 1
                else:
                    dbData[currentWeek][item] = 1
                data["igels"][item]["repeatOffender"] = dbData[currentWeek][item]
            else:
                if item in dbData[currentWeek]:
                    data["igels"][item]["repeatOffender"] = dbData[currentWeek][item]
                else:
                    data["igels"][item]["repeatOffender"] = 0
        else:
            if item in dbData[currentWeek]:
                data["igels"][item]["repeatOffender"] = dbData[currentWeek][item]
            else:
                data["igels"][item]["repeatOffender"] = 0

    # print(dbData)
    with open(db, "w") as ofile:
        json.dump(dbData, ofile)

    return data

def saveDailyFroze(data, db):
    if os.path.isfile(db):
        with open(db, "r") as ifile:
            dbData = json.load(ifile)
            # print("open existing file")
    else:
        dbData = {}
        # print("no file exists")
    # print(dbData)
    currentDate = str(timestamp.strftime("%Y%m%d"))
    # print("{} -- Week: {}".format(timestamp, currentWeek))
    if currentDate in dbData:
        print("currentDate - {} - exists".format(currentDate))
    else:
        print("currentDate - {} - !exists".format(currentDate))
        dbData[currentDate] = {"frozen": [], "unreachable": []}
    print(dbData)
    temp = []
    if data["stats"]["frozen"] > 0:
        for k, v in data["igels"].items():
            # print(k,v)
            if v["unreachable"] == 0:
                # print("unreachable == 0")
                # print(v['broken_percent'], v['verified_percent'])
                if "broken_percent" in v:
                    if v["broken_percent"] >= brokenpercent:
                        print(k,temp)
                        # dbData[currentDate] = dbData[currentDate].append(k.split(".")[0])
                        temp.append(k.split(".")[0])
    print(temp)
    dbData[currentDate]['frozen'] = dbData[currentDate]['frozen'] + temp
    unreachableList = []
    if any(v["repeatOffender"] > 1 for k, v in data["igels"].items()):
        for k, v in data["igels"].items():
            if v["repeatOffender"] > 1:
                if  k.split(".")[0] in dbData[currentDate]['unreachable']:
                    pass
                else:
                    unreachableList.append(k.split(".")[0])
    dbData[currentDate]['unreachable'] = dbData[currentDate]['unreachable'] + unreachableList
    
    print(dbData)
    with open(db, "w") as ofile:
        json.dump(dbData, ofile)

    return data

def getFolder(id, folders):
    for dirs in folders:
        # print(dirs)
        if dirs['parentID'] == id:
            # print(dirs['name'])
            return getFolder(dirs['id'], folders)

def searchBranch(branch, base):
    name = []
    if branch['id'] != "-1":
        parent = [ item for item in base if item['id'] == branch['parentID']]
        if len(parent) > 0:
            name = searchBranch(parent[0], base)
            name.append(branch['name'])
        else:
            name = [branch['name']]
    else:
        name = [branch['name']]
    return name

def getIgelLocation(umsParams):
    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
    try:
        requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += (
            ":HIGH:!DH:!aNULL"
        )
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass
    
    status = requests.get("{}{}".format(umsParams['baseUri'], umsParams['statusStub']), verify=False)
    if status.status_code == 200:
        with requests.Session() as session:
            post = session.post("{}{}".format(umsParams['baseUri'], umsParams['loginStub']), headers=umsParams['headers'], verify=False)
            directoryResults = session.get("{}{}".format(umsParams['baseUri'], umsParams['directoriesStub']), verify=False)
            igelDirectories = directoryResults.json()
            igelsResults = session.get("{}{}".format(umsParams['baseUri'], umsParams['tcStub']), verify=False)
            igels = igelsResults.json()
            session.post("{}{}".format(umsParams['baseUri'], umsParams['logoutStub']), verify=False)
        requests.session().close()

        branchBottoms = []
        folderNames = {}
        for item in igelDirectories:
            # if len(item['DirectoryChildren']) == 0:
            #     branchBottoms.append(item)
            # else:
            #     if any(i['objectType'] == "tcdirectory" for i in item['DirectoryChildren']):
            #         pass
            #     else:
            branchBottoms.append(item)
        
        names = {}
        topLevel = ['Production', "QA", "Testing"]
        for branch in branchBottoms:
            names[branch['id']] = searchBranch(branch, igelDirectories)
            names[branch['id']] = [ x for x in names[branch['id']] if x not in topLevel ]

        # for name in names:
            # print(name, names[name])
        # print(igels[0])
        for igel in igels:
            if igel['parentID'] in names:
                igel['location'] = names[igel['parentID']]
        return igels
    else:
        # print("Status:{}".status)
        return status

def addLocation(igelList, umsData):
    for igel in igelList['igels']:
        # print(igel.split(".")[0])
        igelList['igels'][igel]['location'] = [ "/".join(item['location']) for item in umsData if item['name'] == igel.split(".")[0]]
        # [ print(item) for item in umsData if 'location' not in item]
        # print(igelList['igels'][igel]['location'])
        # if igel.split(".")[0] in umsData:
        #     print(igel)
    return igelList

def generateReport(data, umsData):
    # try:
    for item in data["stats"]:
        if item not in igelList["igels"]:
            # print(item)
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
                # print(task['task']['name'])
                for host in task["hosts"]:
                    # print(host)
                    # print(task['hosts'][host])
                    if "ansible_facts" in task["hosts"][host]:
                        if "verify_match" in task["hosts"][host]["ansible_facts"]:
                            # print("verify_match - host: {}; verify percent: {}".format(host,task["hosts"][host]["ansible_facts"]["verify_match"]["validate"],))
                            igelList["igels"][host]["verified_percent"] = task["hosts"][host]["ansible_facts"]["verify_match"]["validate"]

                            if (igelList["igels"][host]["verified_percent"]> remediationpercent):igelList["stats"]["remediated"] = (igelList["stats"]["remediated"] + 1)
                        if "broken_match" in task["hosts"][host]["ansible_facts"]:
                            # print("broken_match - host: {}; broken percent: {}".format(host,task["hosts"][host]["ansible_facts"]["broken_match"]["match"],))
                            if (task["hosts"][host]["ansible_facts"]["broken_match"]["match"] > brokenpercent):
                                igelList["stats"]["frozen"] = (igelList["stats"]["frozen"] + 1)
                                igelList["stats"]["attemptedremediated"] = (igelList["stats"]["attemptedremediated"] + 1)
                            igelList["igels"][host]["broken_percent"] = task["hosts"][host]["ansible_facts"]["broken_match"]["match"]


    igelListUpdate = repeatOffenders(igelList, db)
    # print("igelListUpdate: {}".format(igelListUpdate))
    saveDailyFroze(igelListUpdate, dailyFrozenDb)
    igelListUpdate = addLocation(igelListUpdate, umsData)
    results = sendemail(timestamp, igelListUpdate)
    # except Exception as e:
    # print("Exception: {}".format(e))
    # print(e)
    # results = {"Internal Server Error": 500}
    # return results


def main(argv):

    try:
        opts, args = getopt.getopt(argv, "h", ["file=", "umsuri="])
        # print(opts)
    except getopt.GetoptError:
        print("file.py --apikey <apikey> --apitoken <apitoken> --board <boardname>")
        sys.exit(2)

    for opt, arg in opts:
        # print(opt)
        if opt == "-h":
            print("test.py --apikey <apikey> --apitoken <apitoken> --board <boardname>")
            sys.exit()
        elif opt in ("-f", "--file"):
            # print(opt,arg)
            datafile = arg
        elif opt in ("-a", "--umsuri"):
            umsData['baseUri'] = arg

    with open(datafile, "r") as ifile:
        data = json.load(ifile)
            # print(data)
    # else:
    #     print("Files does not exists!")
    #     raise
    umsData = getIgelLocation(umsParams)
    generateReport(data, umsData)

    # # Pull list of igels processed
    # for item in data['stats']:
    #     if item not in igelList['igels']:
    #         # print(item)
    #         if data['stats'][item]['unreachable']:
    #             igelList['stats']['unreachable'] = igelList['stats']['unreachable'] + 1
    #         igelList['igels'][item] = { 'unreachable': data['stats'][item]['unreachable'] }

    # igelList['stats']['total_igels'] = len(data['stats'])

    # # Logic to pull specific data
    # for plays in data['plays']:
    #     # print("*******************")
    #     # print(plays['tasks']['task']['name'])
    #     for task in plays['tasks']:
    #         # print(task['task']['name'])
    #         if "set_fact" == task['task']['name']:
    #             # print(task['hosts'])
    #             for host in task['hosts']:
    #                 # print(task['hosts'][host])
    #                 if "verify_match" in task['hosts'][host]["ansible_facts"]:
    #                     # print("Verify_match: {}".format(task['hosts'][host]["ansible_facts"]["verify_match"]['validate']))
    #                     igelList['igels'][host]['verified_percent'] = task['hosts'][host]["ansible_facts"]["verify_match"]['validate']
    #                     igelList['stats']['attemptedremediated'] = igelList['stats']['attemptedremediated'] + 1
    #                     igelList['stats']['frozen'] = igelList['stats']['frozen'] + 1
    #                     if igelList['igels'][host]['verified_percent'] > remediationpercent:
    #                         igelList['stats']['remediated'] = igelList['stats']['remediated'] + 1
    #                 elif "broken_match" in task['hosts'][host]["ansible_facts"]:
    #                     # print("broken_match: {}".format(task['hosts'][host]["ansible_facts"]["broken_match"]['match']))
    #                     igelList['igels'][host]['broken_percent'] = task['hosts'][host]["ansible_facts"]["broken_match"]['match']

    # igelListUpdate = repeatOffenders(igelList, db)
    # sendemail(timestamp, igelListUpdate)
    # print(igelListUpdate)


if __name__ == "__main__":
    main(sys.argv[1:])
