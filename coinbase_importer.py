"""Coinbase JSON file importer

This importer parses a list of accounts, transactions, buy, sells, deposits and widthdrawals in JSON format obtained from the Coinbase API.

Based on Adam Gibbins <adam@adamgibbins.com>'s Monzo API importer.

"""
import datetime
import itertools
import json
import re
from os import path

from beancount.ingest import importer
from beancount.core import data, flags
from beancount.core.number import D
from beancount.utils.date_utils import parse_date_liberally

__author__ = "Jorge Martínez López <jorgeml@jorgeml.me>"
__license__ = "MIT"

VALID_STATUS = ["completed", "failed", "expired", "cancelled"]


def get_account_id(file):
    if not re.match(r'.*\.json', path.basename(file.name)):
        return False

    with open(file.name) as data_file:
        try:
            account_data = json.load(data_file)["account"]
            if "id" in account_data:
                return account_data["id"]
            else:
                return False
        except KeyError:
            return False

def get_account_name(file):
    with open(file.name) as data_file:
        try:
            return json.load(data_file)["account"]["name"]
        except KeyError:
            return None


def get_transactions(file):
    if not re.match(r'.*\.json', path.basename(file.name)):
        return False

    with open(file.name) as data_file:
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
    return data.Amount(unit_price, transaction["native_amount"]["currency"])

def get_payee_account(file, payeeUid, payeeAccountUid):
    with open(file.name) as data_file:
        payee_data = json.load(data_file)["payees"]["payees"]
        for payee in payee_data:
            if payeeUid == payee["payeeUid"]:
                for account in payee["accounts"]:
                    if payeeAccountUid == account["payeeAccountUid"]:
                        return account
        return None


def get_balance(file):
    with open(file.name) as data_file:
        return json.load(data_file)["account"]["balance"]


class Importer(importer.ImporterProtocol):
    def __init__(self, id, account):
        self.id = id
        self.account = account

    def name(self):
        return '{}: "{}"'.format(super().name(), self.account)

    def identify(self, file):
        identifier = get_account_id(file)
        return identifier == self.id

    def extract(self, file, existing_entries=None):
        entries = []
        counter = itertools.count()
        transactions = get_transactions(file)

        for transaction in transactions:

            if transaction["status"] not in VALID_STATUS:
                continue

            tx_description = transaction["description"]
            if tx_description is not None:
                tx_description = tx_description.replace("\n", "")

            metadata = {
                "id": transaction["id"],
                "type": transaction["type"],
                "description": tx_description,
                "created_date": transaction["created_at"],
            }

            meta = data.new_metadata(file.name, next(counter), metadata)

            date = parse_date_liberally(transaction["created_at"])
            price = get_unit_price(transaction)
            payee = None #transaction["counterPartyName"]

            title = None # transaction["details"]["title"]
            subtitle = None # transaction["details"]["subtitle"]
            header = None # transaction["details"]["header"]

            narration = " / ".join(filter(None, [payee, title, subtitle, header]))

            postings = []
            unit = data.Amount(
                D(transaction["amount"]["amount"]),
                transaction["amount"]["currency"],
            )

            postings.append(
                    data.Posting(self.account, unit, None, price, None, None)
                )

            link = set()

            entries.append(
                data.Transaction(
                    meta, date, flags.FLAG_OKAY, payee, narration, set(), link, postings
                )
            )

        balance_date = parse_date_liberally(transactions[-1]["created_at"])
        balance_date += datetime.timedelta(days=1)

        balance = get_balance(file)
        balance_amount = data.Amount(
            D(balance.get("amount")),
            balance.get("currency"),
        )

        meta = data.new_metadata(file.name, next(counter))

        balance_entry = data.Balance(
            meta, balance_date, self.account, balance_amount, None, None
        )

        entries.append(balance_entry)

        return data.sorted(entries)

    def file_account(self, file):
        return self.account

    def file_name(self, file):
        name = get_account_name(file)
        return f"coinbase.{name}.json"

    def file_date(self, file):
        balance = get_balance(file)
        return parse_date_liberally(balance["updated_at"])
