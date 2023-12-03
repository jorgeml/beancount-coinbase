#!/usr/bin/python3

from os import environ, path
from dotenv import load_dotenv
import json
import requests
import sys
import getopt
import random
import string
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

# Find .env file
basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, ".env"))

# General Config
CLIENT_ID = environ.get("CLIENT_ID")
CLIENT_SECRET = environ.get("CLIENT_SECRET")
EMAIL = environ.get("EMAIL")
data_folder = Path(environ.get("DATA_FOLDER"))
API_VERSION = "2022-10-02"

def authenticate():
    state = "".join(
        random.choice(string.ascii_letters + string.digits) for i in range(10)
    )
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "state": state,
        "scope": "wallet:user:read,wallet:accounts:read,wallet:transactions:read,wallet:buys:read,wallet:sells:read,wallet:deposits:read,wallet:withdrawals:read"        
    }
    encoded_params = urllib.parse.urlencode(params)
    login_url = f"https://www.coinbase.com/oauth/authorize?{encoded_params}"
    print(login_url)
    print(
        "Click on the link and copy and paste the authorization code."
    )
    print(f"Check that state is", state)
    auth_code = input("Auth code:")
    return auth_code

def authorize(auth_code):
    headers = {"CB-VERSION": API_VERSION}
    params = {
        "grant_type": "authorization_code",
        "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": auth_code,
    }
    r = requests.post("https://api.coinbase.com/oauth/token", params=params, headers=headers)
    r.raise_for_status()
    access_token = r.json().get("access_token")
    return access_token


def get_accounts(token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {}
    r = requests.get("https://api.coinbase.com/v2/accounts", headers=headers, params=params)
    r.raise_for_status()
    return r.json()

def get_account_information(account, token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {}
    account_id = account.get("id")
    information_request = requests.get(
        f"https://api.coinbase.com/v2/accounts/{account_id}",
        headers=headers,
        params=params,
    )
    information_request.raise_for_status()
    return information_request.json()["data"]

def get_account_transactions(account, token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {"order":"asc"}
    account_id = account.get("id")
    transactions = []
    transactions_request = requests.get(
        f"https://api.coinbase.com/v2/accounts/{account_id}/transactions?expand=all",
        headers=headers,
        params=params,
    )
    transactions_request.raise_for_status()
    transactions_response = transactions_request.json()
    transactions.extend(transactions_response["data"])
    next_uri = transactions_response["pagination"]["next_uri"]
    while (next_uri is not None):
        transactions_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
        )
        transactions_request.raise_for_status()
        transactions_response = transactions_request.json()
        transactions.extend(transactions_response["data"])
        next_uri = transactions_response["pagination"]["next_uri"]
    return transactions

def get_account_deposits(account, token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {"order":"asc"}
    account_id = account.get("id")
    deposits = []
    deposits_request = requests.get(
        f"https://api.coinbase.com/v2/accounts/{account_id}/deposits",
        headers=headers,
        params=params,
    )
    deposits_request.raise_for_status()
    deposits_response = deposits_request.json()
    deposits.extend(deposits_response["data"])
    next_uri = deposits_response["pagination"]["next_uri"]
    while (next_uri is not None):
        deposits_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
        )
        deposits_request.raise_for_status()
        deposits_response = deposits_request.json()
        deposits.extend(deposits_response["data"])
        next_uri = deposits_response["pagination"]["next_uri"]
    return deposits

def get_account_withdrawals(account, token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {"order":"asc"}
    account_id = account.get("id")
    withdrawals = []
    withdrawals_request = requests.get(
        f"https://api.coinbase.com/v2/accounts/{account_id}/withdrawals",
        headers=headers,
        params=params,
    )
    withdrawals_request.raise_for_status()
    withdrawals_response = withdrawals_request.json()
    withdrawals.extend(withdrawals_response["data"])
    next_uri = withdrawals_response["pagination"]["next_uri"]
    while (next_uri is not None):
        withdrawals_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
        )
        withdrawals_request.raise_for_status()
        withdrawals_response = withdrawals_request.json()
        withdrawals.extend(withdrawals_response["data"])
        next_uri = withdrawals_response["pagination"]["next_uri"]
    return withdrawals

def logout(auth_code,token):
    headers = {"Authorization": f"Bearer {token}", "CB-VERSION": API_VERSION}
    params = {"token": auth_code}
    r = requests.post("https://api.coinbase.com/oauth/revoke", headers=headers, params=params)
    r.raise_for_status()
    print("Log out successful")

def main(argv):
    auth_code = authenticate()
    token = authorize(auth_code)
    accounts = get_accounts(token)
    for account in accounts.get("data"):
        if account.get("created_at") is None:
            continue
        entries = {}
        entries["account"]=get_account_information(account, token)
        entries["transactions"]=get_account_transactions(account, token)
        entries["deposits"]=get_account_deposits(account, token)
        entries["withdrawals"]=get_account_withdrawals(account, token)
        account_name = account.get("name")
        filename = data_folder / f"{date.today()}-coinbase-{account_name}.json"
        with open(filename, "w") as json_file:
                json.dump(entries, json_file, indent=2, ensure_ascii=False)
    logout(auth_code,token)

if __name__ == "__main__":
    main(sys.argv[1:])
