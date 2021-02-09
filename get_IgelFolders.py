import requests
import urllib3
import time
import json
# import pandas as pd

serverName = "SERVERNAME"
loginUri = "https://{}:8443/umsapi/v3/login".format(serverName)
logoutUri = "https://{}:8443/umsapi/v3/logout".format(serverName)
directoriesUri = (
    "https://{}:8443/umsapi/v3/directories/tcdirectories?facets=children".format(serverName)
)
headers = {"Authorization": "Basic BASE64-ENCODED-PASS"}
timestr = time.strftime("%Y%m%d-%H%M%S")

def getFolder(id, folders):
    for dirs in folders:
        # print(dirs)
        if dirs['parentID'] == id:
            print(dirs['name'])
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

def main():

    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ":HIGH:!DH:!aNULL"
    try:
        requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += (
            ":HIGH:!DH:!aNULL"
        )
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass

    status = requests.get("https://{}:8443/umsapi/v3/serverstatus".format(serverName), verify=False)

    if status.status_code == 200:
        with requests.Session() as session:
            post = session.post(loginUri, headers=headers, verify=False)

            directoryResults = session.get(directoriesUri, verify=False)

            igelDirectories = directoryResults.json()
            session.post(logoutUri, verify=False)

        requests.session().close()

        branchBottoms = []
        folderNames = {}
        for item in igelDirectories:
            branchBottoms.append(item)
     
        names = {}
        topLevel = ['Production', "QA", "Testing"]
        for branch in branchBottoms:
            names[branch['id']] = searchBranch(branch, igelDirectories)
            names[branch['id']] = [ x for x in names[branch['id']] if x not in topLevel ]

        for name in sorted(names.keys()) :  
            print(name, names[name])

    else:
        pass


if __name__ == "__main__":
    main()
