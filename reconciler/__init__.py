import os
import re
import datetime
import importlib
import gocardless_pro
from openpyxl import Workbook
from reconciler.mail import drivers

class Reconciler :

    _mail      = None # Parameters used for sending result by mail
    _mailer    = None # Mail driver class
    _client    = None # GoCardless client
    _book      = None # Output xlsx wookbook
    _sheet     = None # Output xlsx worksheet

    _limit     = None # How are we limiting getting results from GC
    _ldate     = None # Date to limit by

    _payouts   = {}   # Returned list of payout items
    _payments  = []   # Returned list of payments
    _matched   = []   # Payouts matched to payments

    _filename  = None # File to export payments to
    _exported  = None # Exported xlsx file of matches

    _columns   = None # Keys for custom xlsx columns
    _headings  = None # Custom xlsx headings
    _parser    = None # Custom payment description parser

    def __init__(self, **args) :
        if ("mail" in args) :
            self._mail = args["mail"]

            driver = drivers[self._mail["driver"]]
            mailer = importlib.import_module(driver[0] , package='reconciler.mail')
            self._mailer = getattr(mailer, driver[1])(self._mail)

        if ("gc" in args and "token" in args["gc"]) :
            self._client = gocardless_pro.Client(
                access_token = args["gc"]["token"],
                environment = args["gc"]["environment"] if ("environment" in args["gc"]) else "live"
            )

        else :
            raise ValueError("GoCardless token missing - check parameters")

        if ("columns" in args) :
            self._columns = args["columns"]
            self._headings = args["headings"] if ("headings" in args) else args["columns"]

        else :
            self._defaultColumns()

        self._parser = args["parser"] if ("parser" in args) else None

        self._filename = args["file"] if ("file" in args) else "export.xlsx"
        self._book = Workbook(write_only = True)
        self._sheet = self._book.create_sheet()
        self._headerRow()

        self._limit = args["limit"] if ("limit" in args) else "month"
        self._calculateDateLimit()

    def _calculateDateLimit(self) :
        today = datetime.datetime.today()

        if self._limit == "week" :
            l = (today - datetime.timedelta(weeks=1))

        elif self._limit == "month" :
            l = (today - datetime.timedelta(days=31))

        elif self._limit == "year" :
            l = (today - datetime.timedelta(weeks=52))

        elif self._limit == "calyear" :
            l = datetime.datetime(today.year, 1, 1, 0, 0, 0)

        elif self._limit == "finyear" :
            year = (today.year) if today.month > 3 else (today.year - 1)
            l = datetime.datetime(year, 4, 1, 0, 0, 0)

        elif self._limit == "all" :
            l = datetime.datetime(1970, 1, 1, 0, 0, 0)
        else :
            raise ValueError("Incorrect limit specified")

        self._ldate = l.strftime("%Y-%m-%dT00:00:00.000") + "Z"

    def _headerRow(self) :
        self._sheet.append(self._headings)

    def _defaultColumns(self) :
        self._columns = [
            "payout_date",
            "payout_reference",
            "payment_amount_net",
            "payment_description_schedule",
            "payment_description_event"
        ]

        self._headings = [
            "Payout Date",
            "Payout Reference",
            "Amount",
            "Schedule",
            "Event"
        ]

    def _fetchPayoutItems(self, after = False) :
        # A 'payout' is a transfer of money from GoCardless to the account.
        # Payouts consist of several payout items, some of these being the payments in
        # that have come via OSM.

        params = {
            "status"          : "paid",
            "created_at[gte]" : self._ldate,
            "limit"           : 500
        }

        if after :
            params["after"] = after

        payouts = self._client.payouts.list(params = params)

        for p in payouts.records :
            items = self._client.payout_items.list(params = {
                "payout" : p.id
            }).records

            for i in items :
                if i.type == "payment_paid_out" :
                    self._payouts[p.id] = {
                        "payout_date"      : p.arrival_date,
                        "payout_reference" : p.reference,
                        "payment_id"       : i.links.payment
                    }

        if payouts.after :
            self._fetchPayouts(payouts.after)

    def _fetchPayments(self, after = False) :
        # A 'payment' is the transfer of money from a customer to GoCardless.
        # Payments are bundled together along with GoCardless/OSM fees to make a payout.

        params = {
            "status" : "paid_out",
            "created_at[gte]" : self._ldate,
            "limit"  : 500
        }

        if after :
            params["after"] = after

        payments = self._client.payments.list(params = params)

        for p in payments.records :
            payout = {
                "payout_id"            : p.links.payout,
                "payment_id"           : p.id,
                "payment_date"         : p.charge_date,
                "payment_amount_gross" : round((p.amount / 100), 2),
                "payment_amount_net"   : self._calculateNet(p.amount),
                "payment_description"  : p.description,
                "member_name"          : p.metadata["Member"]
            }
            parsed = self._parseDescription(p.description)
            self._payments.append({ **payout, **parsed })

        if payments.after :
            self._fetchPayments(payments.after)

    def _matchPayoutItemsWithPayments(self) :
        for p in self._payments :
            try :
                payout = self._payouts[p["payout_id"]]
                r = { **p, **payout }

                self._matched.append(r)
                self._sheet.append([ r[k] for k in self._columns ])

            except (KeyError) :
                raise Exception("Missing Payment!") # This shouldn't happen!

    def _parseDescription(self, description) :
        if self._parser :
            return self._parser(description)
        else:
            pattern = re.compile("([\w\W]+) \(([\w\W]+)\)")
            match = pattern.findall(description)
            match = match[0] if (len(match) > 0) else ["", ""]

        return {
            "payment_description_schedule" : match[0],
            "payment_description_event"    : match[1]
        }

    def _calculateNet(self, amount) :
        # Fees are 2.95% if over £15, or (1.95% + 15p) if under
        amount = amount / 100
        if amount < 15 :
            fee = (0.0195 * amount) + 0.15
        else :
            fee = (0.0295 * amount)

        return round((amount - fee), 2)

    def _deleteExported(self) :
        os.remove(self._exported)

    def reconcile(self) :
        self._fetchPayoutItems()
        self._fetchPayments()
        self._matchPayoutItemsWithPayments()

        return self

    def export(self) :
        self._book.save(self._filename)
        self._exported = self._filename

        return self

    def send(self, keepExported = False) :
        if(not self._mailer) :
            raise ValueError("Mail driver not specified, or loaded incorrectly - check mail parameters")

        if(not self._exported) :
            self.export()

        duration = {
            "week"    : "the past week",
            "month"   : "the past 31 days",
            "year"    : "the past year",
            "calyear" : "this calendar year",
            "finyear" : "this financial year",
            "all"     : "all time"
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
            "GoCardless payments for {} are attached.\n\nGoCardless reconciliation powered by https://github.com/cabotexplorers/reconciler.".format(duration[self._limit])
        )
        self._mailer.send()

        if not keepExported :
            self._deleteExported()

        return self
