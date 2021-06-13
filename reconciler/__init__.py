import os
import re
import datetime
import importlib
import decimal

import gocardless_pro
from openpyxl import Workbook

from reconciler.mail import drivers


class Reconciler:

    _mail = None  # Parameters used for sending result by mail
    _mailer = None  # Mail driver class
    _client = None  # GoCardless client
    _book = None  # Output xlsx wookbook
    _sheet = None  # Output xlsx worksheet

    _limit = None  # How are we limiting getting results from GC
    _ldate = None  # Date to limit by

    _payouts = {}  # Returned dict of payout items (keyed by payment ID)
    _payments = []  # Returned list of payments
    _matched = []  # Payouts matched to payments

    _filename = None  # File to export payments to
    _exported = None  # Exported xlsx file of matches

    _columns = None  # Keys for custom xlsx columns
    _headings = None  # Custom xlsx headings
    _parser = None  # Custom payment description parser

    def __init__(self, **args):
        if "mail" in args:
            self._mail = args["mail"]

            driver = drivers[self._mail["driver"]]
            mailer = importlib.import_module(driver[0], package="reconciler.mail")
            self._mailer = getattr(mailer, driver[1])(self._mail)

        if "gc" in args and "token" in args["gc"]:
            self._client = gocardless_pro.Client(
                access_token=args["gc"]["token"],
                environment=args["gc"]["environment"]
                if ("environment" in args["gc"])
                else "live",
            )

        else:
            raise ValueError("GoCardless token missing - check parameters")

        if "columns" in args:
            self._columns = args["columns"]
            self._headings = (
                args["headings"] if ("headings" in args) else args["columns"]
            )

        else:
            self._defaultColumns()

        self._parser = args["parser"] if ("parser" in args) else None

        self._filename = args["file"] if ("file" in args) else "export.xlsx"
        self._book = Workbook(write_only=True)
        self._sheet = self._book.create_sheet()
        self._headerRow()

        self._limit = args["limit"] if ("limit" in args) else "month"
        self._calculateDateLimit()

    def _calculateDateLimit(self):
        today = datetime.datetime.today()

        if self._limit == "week":
            l = today - datetime.timedelta(weeks=1)

        elif self._limit == "month":
            l = today - datetime.timedelta(days=31)

        elif self._limit == "year":
            l = today - datetime.timedelta(weeks=52)

        elif self._limit == "calyear":
            l = datetime.datetime(today.year, 1, 1, 0, 0, 0)

        elif self._limit == "finyear":
            year = (today.year) if today.month > 3 else (today.year - 1)
            l = datetime.datetime(year, 4, 1, 0, 0, 0)

        elif self._limit == "all":
            l = datetime.datetime(1970, 1, 1, 0, 0, 0)
        else:
            raise ValueError("Incorrect limit specified")

        self._ldate = l.strftime("%Y-%m-%dT00:00:00.000") + "Z"

    def _headerRow(self):
        self._sheet.append(self._headings)

    def _defaultColumns(self):
        self._columns = [
            "payout_date",
            "payout_reference",
            "payment_amount_net",
            "payment_description_schedule",
            "payment_description_event",
        ]

        self._headings = [
            "Payout Date",
            "Payout Reference",
            "Amount",
            "Schedule",
            "Event",
        ]

    def _fetchPayouts(self, after=False):
        # A 'payout' is a transfer of money from GoCardless to a bank account.
        # https://developer.gocardless.com/api-reference/#core-endpoints-payouts

        params = {"status": "paid", "created_at[gte]": self._ldate, "limit": 500}

        if after:
            params["after"] = after

        payouts = self._client.payouts.list(params=params)

        for payout in payouts.records:
            event = (
                self._client.events.list({"action": "paid", "payout": payout.id})
                .records[0]
                .id
            )

            self._payouts[payout.id] = {
                "payout_date": payout.arrival_date,
                "payout_reference": payout.reference,
                "payout_event": event,
            }

        if payouts.after:
            self._fetchPayouts(payouts.after)

    def _fetchPayoutEvents(self):
        # Each payout has a payout_event associated with it, created when the payout is actually paid
        # https://developer.gocardless.com/api-reference/#core-endpoints-events
        for payout in self._payouts:
            self._fetchChildEvents(self._payouts[payout]["payout_event"])

    def _fetchChildEvents(self, parent, after=False):
        # Each child event represents one of the payments making up the payout coming in
        # https://developer.gocardless.com/api-reference/#events-reconciling-payouts-with-events
        params = {
            "resource_type": "payments",
            "include": "payment",
            "parent_event": parent,
        }

        if after:
            params["after"] = after

        events = self._client.events.list(params=params)
        records = events.records

        for record in records:
            payment = self._client.payments.get(record.links.payment)

            fees = self._calculateFees(payment.amount)

            data = {
                "payout_id": payment.links.payout,
                "payment_id": payment.id,
                "payment_date": payment.charge_date,
                "payment_description": payment.description,
                "payment_amount_gross": round(payment.amount / 100, 2),
                "payment_amount_net": round((payment.amount - fees) / 100, 2),
                "payment_amount_fees": round(fees / 100, 2),
                "member_name": payment.metadata["Member"],
            }
            parsed = self._parseDescription(payment.description)
            payout = self._payouts[payment.links.payout]

            matched = {**data, **parsed, **payout}

            self._matched.append(matched)
            self._sheet.append([matched.get(k, "") for k in self._columns])

        if events.after:
            self._fetchChildEvents(parent, events.after)

    def _calculateFees(self, amount):
        amount = decimal.Decimal(amount)  # Amount in whole pence

        gc = (max(decimal.Decimal(15.0), decimal.Decimal(0.01) * amount)).quantize(
            decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP
        )  # 1% of amount, or 15p, whichever's higher

        gc_vat = (gc * decimal.Decimal(0.2)).quantize(
            decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP
        )  # 20% VAT on GC fees - quantized to whole pence

        osm = (decimal.Decimal(0.0195) * amount).quantize(
            decimal.Decimal(1), rounding=decimal.ROUND_HALF_UP
        )  # 1.95% of amount - quantized to whole pence

        return int(gc + gc_vat + osm)

    def _parseDescription(self, description):
        if self._parser:
            return self._parser(description)
        else:
            pattern = re.compile("([\w\W]+) \(([\w\W]+)\)")
            match = pattern.findall(description)
            match = match[0] if (len(match) > 0) else ["", ""]

        return {
            "payment_description_schedule": match[0],
            "payment_description_event": match[1],
        }

    def reconcile(self):
        self._fetchPayouts()
        self._fetchPayoutEvents()

        return self

    def export(self):
        self._book.save(self._filename)
        self._exported = self._filename

        return self

    def send(self, keepExported=False):
        if not self._mailer:
            raise ValueError(
                "Mail driver not specified, or loaded incorrectly - check mail parameters"
            )

        if not self._exported:
            self.export()

        duration = {
            "week": "the past week",
            "month": "the past 31 days",
            "year": "the past year",
            "calyear": "this calendar year",
            "finyear": "this financial year",
            "all": "all time",
        }

        to = self._mail["to"] if ("to" in self._mail) else []
        cc = self._mail["cc"] if ("cc" in self._mail) else []
        bcc = self._mail["bcc"] if ("bcc" in self._mail) else []

        self._mailer.subject("GoCardless Payment Reconciliation")
        self._mailer.to(to)
        self._mailer.cc(cc)
        self._mailer.bcc(bcc)
        self._mailer.sender(self._mail["from"])
        self._mailer.attach(self._exported)
        self._mailer.message(
            "GoCardless payments for {} are attached.\n\nGoCardless reconciliation powered by https://github.com/cabotexplorers/reconciler.".format(
                duration[self._limit]
            )
        )
        self._mailer.send()

        if not keepExported:
            os.remove(self._exported)

        return self
