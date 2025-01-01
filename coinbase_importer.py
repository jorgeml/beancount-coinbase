"""Coinbase JSON file importer

This importer parses a list of accounts, transactions, buy, sells, deposits and widthdrawals in JSON format obtained from the Coinbase API.

Based on Adam Gibbins <adam@adamgibbins.com>'s Monzo API importer.

"""

__author__ = "Jorge Martínez López <jorgeml@jorgeml.me>"
__license__ = "MIT"

import datetime
import itertools
import json
import re

from os import path

from beancount.core import account
from beancount.core import amount
from beancount.core import data
from beancount.core import flags
from beancount.core import position
from beancount.core.number import D
from beancount.core.number import ZERO

import beangulp
from beangulp import mimetypes
from beangulp.testing import main

VALID_STATUS = ["completed", "failed", "expired", "cancelled"]

class Importer(beangulp.Importer):
    """An importer for Coinbase API JSON files."""

    def __init__(self, account_id, account):
        self.account_id = account_id
        self.importer_account = account

    def identify(self, filepath):
        identifier = get_account_id(filepath)
        return identifier == self.account_id

    def filename(self, filepath):
        account_name = get_account_name(filepath)
        return f'coinbase.{account_name}.json'
    
    def account(self, filepath):
        return self.importer_account

    def date(self, filepath):
        transactions = get_transactions(filepath)
        return parse_transaction_time(transactions[-1]["created_at"])

    def extract(self, filepath, existing=None):
        entries = []
        counter = itertools.count()
        transactions = get_transactions(filepath)

        for transaction in transactions:

            if transaction["status"] not in VALID_STATUS:
                continue

            #tx_description = transaction["description"]
            #if tx_description is not None:
            #    tx_description = tx_description.replace("\n", "")

            metadata = {
                "id": transaction["id"],
                "type": transaction["type"],
                #"description": tx_description,
                "created_date": transaction["created_at"],
            }

            meta = data.new_metadata(filepath, next(counter), metadata)

            date = parse_transaction_time(transaction["created_at"])
            price = get_unit_price(transaction)
            payee = None #transaction["counterPartyName"]

            title = None # transaction["details"]["title"]
            subtitle = None # transaction["details"]["subtitle"]
            header = None # transaction["details"]["header"]

            narration = " / ".join(filter(None, [payee, title, subtitle, header]))

            postings = []
            unit = amount.Amount(
                D(transaction["amount"]["amount"]),
                transaction["amount"]["currency"],
            )

            postings.append(
                    data.Posting(self.importer_account, unit, None, price, None, None)
                )

            link = set()

            entries.append(
                data.Transaction(
                    meta, date, flags.FLAG_OKAY, payee, narration, set(), link, postings
                )
            )

        balance_date = parse_transaction_time(transactions[-1]["created_at"])
        balance_date += datetime.timedelta(days=1)

        balance = get_balance(filepath)
        balance_amount = amount.Amount(
            D(balance.get("amount")),
            balance.get("currency"),
        )

        meta = data.new_metadata(filepath, next(counter))

        balance_entry = data.Balance(
            meta, balance_date, self.importer_account, balance_amount, None, None
        )

        entries.append(balance_entry)

        return data.sorted(entries)


def get_account_id(filepath):
    mimetype, encoding = mimetypes.guess_type(filepath)
    if mimetype != 'application/json':
        return False

    with open(filepath) as data_file:
        try:
            account_data = json.load(data_file)["account"]
            if "id" in account_data:
                return account_data["id"]
            else:
                return False
        except KeyError:
            return False

def get_account_name(filepath):
    with open(filepath) as data_file:
        try:
            return json.load(data_file)["account"]["name"]
        except KeyError:
            return None


def get_transactions(filepath):
    mimetype, encoding = mimetypes.guess_type(filepath)
    if mimetype != 'application/json':
        return False

    with open(filepath) as data_file:
        try:
            return json.load(data_file)["transactions"]
        except KeyError:
            print("No transactions in file.")
            return False


def get_unit_price(transaction):
    total_amount = D(transaction["amount"]["amount"])
    total_native_amount = D(transaction["native_amount"]["amount"])
    # all prices need to be positive
    unit_price = round(abs(total_native_amount / total_amount), 5)
    return amount.Amount(unit_price, transaction["native_amount"]["currency"])

def get_payee_account(filepath, payeeUid, payeeAccountUid):
    with open(filepath) as data_file:
        payee_data = json.load(data_file)["payees"]["payees"]
        for payee in payee_data:
            if payeeUid == payee["payeeUid"]:
                for account in payee["accounts"]:
                    if payeeAccountUid == account["payeeAccountUid"]:
                        return account
        return None

def get_balance(filepath):
    with open(filepath) as data_file:
        return json.load(data_file)["account"]["balance"]

def parse_transaction_time(date_str):
    """Parse a time string and return a datetime object.

    Args:
      date_str: A string, the date to be parsed, in ISO format.
    Returns:
      A datetime.date() instance.
    """
    timestamp = datetime.datetime.fromisoformat(date_str)
    return timestamp.date()

