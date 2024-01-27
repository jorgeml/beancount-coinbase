#!/usr/bin/python3

from os import environ, path
from dotenv import load_dotenv
import json
import hmac
import hashlib
import requests
import sys
import getopt
import random
import string
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path
from requests.auth import AuthBase

# Find .env file
basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, ".env"))

# General Config
API_KEY = environ.get("API_KEY")
API_SECRET = environ.get("API_SECRET")
data_folder = Path(environ.get("DATA_FOLDER"))
API_VERSION = "2022-10-02"


# Coinbase Authentication code from https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-key-authentication
# Create custom authentication for Coinbase API
class CoinbaseWalletAuth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or "")
        signature = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        request.headers.update(
            {
                "CB-ACCESS-SIGN": signature,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-ACCESS-KEY": self.api_key,
            }
        )
        return request


api_url = "https://api.coinbase.com/v2/"
auth = CoinbaseWalletAuth(API_KEY, API_SECRET)


def get_accounts():
    headers = {"CB-VERSION": API_VERSION}
    params = {}
    accounts = []
    accounts_request = requests.get(
        api_url + "accounts", headers=headers, params=params, auth=auth
    )
    accounts_request.raise_for_status()
    accounts_response = accounts_request.json()
    accounts.extend(accounts_response["data"])
    next_uri = accounts_response["pagination"]["next_uri"]
    while next_uri is not None:
        accounts_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
            auth=auth,
        )
        accounts_request.raise_for_status()
        accounts_response = accounts_request.json()
        accounts.extend(accounts_response["data"])
        next_uri = accounts_response["pagination"]["next_uri"]
    return accounts


def get_account_information(account):
    headers = {"CB-VERSION": API_VERSION}
    params = {}
    account_id = account.get("id")
    information_request = requests.get(
        api_url + f"accounts/{account_id}",
        headers=headers,
        params=params,
        auth=auth,
    )
    information_request.raise_for_status()
    return information_request.json()["data"]


def get_account_transactions(account):
    headers = {"CB-VERSION": API_VERSION}
    params = {"expand": "all", "order": "asc"}
    account_id = account.get("id")
    transactions = []
    transactions_request = requests.get(
        api_url + f"accounts/{account_id}/transactions",
        headers=headers,
        params=params,
        auth=auth,
    )
    transactions_request.raise_for_status()
    transactions_response = transactions_request.json()
    transactions.extend(transactions_response["data"])
    next_uri = transactions_response["pagination"]["next_uri"]
    while next_uri is not None:
        transactions_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
            auth=auth,
        )
        transactions_request.raise_for_status()
        transactions_response = transactions_request.json()
        transactions.extend(transactions_response["data"])
        next_uri = transactions_response["pagination"]["next_uri"]
    return transactions


def get_account_deposits(account):
    headers = {"CB-VERSION": API_VERSION}
    params = {"order": "asc"}
    account_id = account.get("id")
    deposits = []
    deposits_request = requests.get(
        api_url + f"accounts/{account_id}/deposits",
        headers=headers,
        params=params,
        auth=auth,
    )
    deposits_request.raise_for_status()
    deposits_response = deposits_request.json()
    deposits.extend(deposits_response["data"])
    next_uri = deposits_response["pagination"]["next_uri"]
    while next_uri is not None:
        deposits_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
            auth=auth,
        )
        deposits_request.raise_for_status()
        deposits_response = deposits_request.json()
        deposits.extend(deposits_response["data"])
        next_uri = deposits_response["pagination"]["next_uri"]
    return deposits


def get_account_withdrawals(account):
    headers = {"CB-VERSION": API_VERSION}
    params = {"order": "asc"}
    account_id = account.get("id")
    withdrawals = []
    withdrawals_request = requests.get(
        api_url + f"accounts/{account_id}/withdrawals",
        headers=headers,
        params=params,
        auth=auth,
    )
    withdrawals_request.raise_for_status()
    withdrawals_response = withdrawals_request.json()
    withdrawals.extend(withdrawals_response["data"])
    next_uri = withdrawals_response["pagination"]["next_uri"]
    while next_uri is not None:
        withdrawals_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
            auth=auth,
        )
        withdrawals_request.raise_for_status()
        withdrawals_response = withdrawals_request.json()
        withdrawals.extend(withdrawals_response["data"])
        next_uri = withdrawals_response["pagination"]["next_uri"]
    return withdrawals


def main(argv):
    accounts = get_accounts()
    for account in accounts:
        if account.get("created_at") is None:
            continue
        entries = {}
        entries["account"] = get_account_information(account)
        entries["transactions"] = get_account_transactions(account)
        entries["deposits"] = get_account_deposits(account)
        entries["withdrawals"] = get_account_withdrawals(account)
        account_name = account.get("name")
        filename = data_folder / f"{date.today()}-coinbase-{account_name}.json"
        with open(filename, "w") as json_file:
            json.dump(entries, json_file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
