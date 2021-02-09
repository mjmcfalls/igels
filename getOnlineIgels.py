import requests
import urllib3
import time
import json
import pandas as pd
loginUri = 'https://SERVER-ADDRESS:8443/umsapi/v3/login'
logoutUri = 'https://SERVER-ADDRESS:8443/umsapi/v3/logout'
onlineUri = "https://SERVER-ADDRESS:8443/umsapi/v3/thinclients?facets=online"
detailsUri = "https://SERVER-ADDRESS:8443/umsapi/v3/thinclients?facets=details"
headers = {"Authorization": "Basic BASE64-ENCODED-PASS"}
timestr = time.strftime("%Y%m%d-%H%M%S")

def main():

    requests.packages.urllib3.disable_warnings()
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    try:
        requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
    except AttributeError:
        # no pyopenssl support used / needed / available
        pass

    status = requests.get('https://SERVER-ADDRESS:8443/umsapi/v3/serverstatus', verify=False)
    # print(status.status_code)
    if(status.status_code == 200):
        with requests.Session() as session:
            post = session.post(loginUri, headers=headers, verify=False)
            igelDetails = session.get(detailsUri, verify=False)
            igelsOnline = session.get(onlineUri, verify=False)

            detailsDf = pd.read_json(path_or_buf=igelDetails.content)


            noSkipDf = detailsDf[~detailsDf['comment'].str.contains("#skip", na=False)]
            print(noSkipDf)
            session.post(logoutUri, verify=False)

        requests.session().close()
    else: 
        pass


if __name__ == "__main__":
    main()
