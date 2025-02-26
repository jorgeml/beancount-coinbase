#!/usr/bin/python3

from cryptography.hazmat.primitives import serialization
from datetime import date, timedelta
from dotenv import load_dotenv
from os import environ, path
from pathlib import Path
from requests.auth import AuthBase
import hashlib
import hmac
import json
import jwt
import random
import requests
import secrets
import sys
import time
import urllib.parse

# Find .env file
basedir = path.abspath(path.dirname(__file__))
load_dotenv(path.join(basedir, ".env"))

# General Config
key_name = environ.get("API_KEY_NAME")
key_secret = environ.get("API_KEY_SECRET")
data_folder = Path(environ.get("DATA_FOLDER"))


def build_jwt(uri):
    private_key_bytes = key_secret.encode('utf-8')
    private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
    jwt_payload = {
        'sub': key_name,
        'iss': "cdp",
        'nbf': int(time.time()),
        'exp': int(time.time()) + 120,
        'uri': uri,
    }
    jwt_token = jwt.encode(
        jwt_payload,
        private_key,
        algorithm='ES256',
        headers={'kid': key_name, 'nonce': secrets.token_hex()},
    )
    return jwt_token


request_method = "GET"
request_host   = "api.coinbase.com"


def get_accounts():
    request_path = "/v2/accounts"
    uri = f"{request_method} {request_host}{request_path}"
    jwt_token = build_jwt(uri)
    headers = {'Authorization': 'Bearer {}'.format(jwt_token)}
    params = {}
    accounts = []
    accounts_request = requests.get(
        "https://" + request_host + request_path, headers=headers, params=params
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
        )
        accounts_request.raise_for_status()
        accounts_response = accounts_request.json()
        accounts.extend(accounts_response["data"])
        next_uri = accounts_response["pagination"]["next_uri"]
    return accounts


def get_account_information(account):
    account_id = account.get("id")
    request_path = f"/v2/accounts/{account_id}"
    uri = f"{request_method} {request_host}{request_path}"
    jwt_token = build_jwt(uri)
    headers = {'Authorization': 'Bearer {}'.format(jwt_token)}
    params = {}
    information_request = requests.get(
        "https://" + request_host + request_path,
        headers=headers,
        params=params,
    )
    information_request.raise_for_status()
    return information_request.json()["data"]


def get_account_transactions(account):
    account_id = account.get("id")
    request_path = f"/v2/accounts/{account_id}/transactions"
    uri = f"{request_method} {request_host}{request_path}"
    jwt_token = build_jwt(uri)
    headers = {'Authorization': 'Bearer {}'.format(jwt_token)}
    params = {"expand": "all", "order": "asc"}
    transactions = []
    transactions_request = requests.get(
        "https://" + request_host + request_path,
        headers=headers,
        params=params,
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
        )
        transactions_request.raise_for_status()
        transactions_response = transactions_request.json()
        transactions.extend(transactions_response["data"])
        next_uri = transactions_response["pagination"]["next_uri"]
    return transactions


def get_account_deposits(account):
    account_id = account.get("id")
    request_path = f"/v2/accounts/{account_id}/deposits"
    uri = f"{request_method} {request_host}{request_path}"
    jwt_token = build_jwt(uri)
    headers = {'Authorization': 'Bearer {}'.format(jwt_token)}
    params = {"order": "asc"}
    deposits = []
    deposits_request = requests.get(
        "https://" + request_host + request_path,
        headers=headers,
        params=params,
    )
    deposits_request.raise_for_status()
    deposits_response = deposits_request.json()
    deposits.extend(deposits_response["data"])
    next_uri = deposits_response["pagination"].get("next_uri")
    while next_uri:
        deposits_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
        )
        deposits_request.raise_for_status()
        deposits_response = deposits_request.json()
        deposits.extend(deposits_response["data"])
        next_uri = deposits_response["pagination"].get("next_uri")
    return deposits


def get_account_withdrawals(account):
    account_id = account.get("id")
    request_path = f"/v2/accounts/{account_id}/withdrawals"
    uri = f"{request_method} {request_host}{request_path}"
    jwt_token = build_jwt(uri)
    headers = {'Authorization': 'Bearer {}'.format(jwt_token)}
    params = {"order": "asc"}
    withdrawals = []
    withdrawals_request = requests.get(
        "https://" + request_host + request_path,
        headers=headers,
        params=params,
    )
    withdrawals_request.raise_for_status()
    withdrawals_response = withdrawals_request.json()
    withdrawals.extend(withdrawals_response["data"])
    next_uri = withdrawals_response["pagination"].get("next_uri")
    while next_uri:
        withdrawals_request = requests.get(
            f"https://api.coinbase.com{next_uri}",
            headers=headers,
            params={},
        )
        withdrawals_request.raise_for_status()
        withdrawals_response = withdrawals_request.json()
        withdrawals.extend(withdrawals_response["data"])
        next_uri = withdrawals_response["pagination"].get("next_uri")
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
