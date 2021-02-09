#!/usr/bin/python

from __future__ import (absolute_import, division, print_function)
import os
import sys
import argparse
import requests
import time
import pandas as pd

__metaclass__ = type

timestr = time.strftime("%Y%m%d-%H%M%S")
domain = "msj.org"
try:
    import json
except ImportError:
    import simplejson as json

class igelInventory(object):
    serverAddress = "SERVERADDRESS"
    loginUri = 'https://{}:8443/umsapi/v3/login'.format(serverAddress)
    logoutUri = 'https://{}:8443/umsapi/v3/logout'.format(serverAddress)
    # onlineUri = "https://{}:8443/umsapi/v3/thinclients?facets=online".format(serverAddress)
    detailsUri = "https://{}:8443/umsapi/v3/thinclients?facets=details".format(serverAddress)
    serverStatusUri = 'https://{}:8443/umsapi/v3/serverstatus'.format(serverAddress)
    headers = {"Authorization": "Basic BASE64-ENCODED-PASS"}
    igels = None
    removedFromService = "351472"

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        # Called with `--list`.
        if self.args.list:
            self.inventory = self.igel_inventory()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = { self.args.host: {'host_specific_var': 'igels'}}
        # If no groups or vars are present, return an empty inventory.
        else:
            self.inventory = self.empty_inventory()

        print(self.inventory)

    def get_igels(self):
        requests.packages.urllib3.disable_warnings()
        requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
        try:
            requests.packages.urllib3.contrib.pyopenssl.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'
        except AttributeError:
            # no pyopenssl support used / needed / available
            pass

        status = requests.get(self.serverStatusUri, verify=False)
        # print(status.status_code)
        if(status.status_code == 200):
            with requests.Session() as session:
                # print("Posting creds")
                post = session.post(self.loginUri, headers=self.headers, verify=False)
                # print(post)
                igels = session.get(self.detailsUri, verify=False)
                # print(igels.json())
                # self.igels = igels.json()
                detailsDf = pd.read_json(path_or_buf=igels.content)
                noSkipDf = detailsDf[~detailsDf['comment'].str.contains("#skip", na=False)]
                returnDf = noSkipDf[noSkipDf.parentID != self.removedFromService]
                session.post(self.logoutUri, verify=False)
            requests.session().close()
            # igels = returnDf #.to_json(orient='records')[0]
        return noSkipDf

    def igel_inventory(self):
        igels = self.get_igels()
        hosts = []
        hostvars = {}

        for igel in igels.itertuples():
            if igel.networkName:
                hosts.append("{}.{}".format(igel.networkName,domain))
                hostvars["{}.{}".format(igel.networkName,domain)] = {}

        self.inventory['igels'] = {"hosts": hosts, 'vars':{}}
        self.inventory['_meta'] = {}
        self.inventory['_meta']['hostvars'] = hostvars
        # with open('src/igelInventory_{}.json'.format(timestr), 'w') as outfile:
        #     json.dump(self.inventory, outfile)
        return json.dumps(self.inventory)
    # Empty inventory for testing.
    def empty_inventory(self):
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

igelInventory()
