import datetime
import importlib
import gocardless_pro
from reconciler.mail import drivers

# TODO: fix correct driver being imported
from reconciler.mail.mailgun import Mailgun

class Reconciler :

	_mail     = None # Parameters used for sending result by mail
	_mailer   = None # Mail driver class
	_client   = None # GoCardless client
	
	_limit    = None # How are we limiting getting results from GC
	_ldate    = None # Date to limit by

	_payouts  = []   # Returned list of payouts
	_payments = {}   # Returned list of payments
	_matched  = []   # Payouts matched to payments
	_exported = None # Exported xlsx file of matches

	def __init__(self, gc, params, limit = "month") :
		self._mail = params

		driver = drivers[params["driver"]]
		# mailer = importlib.import_module(driver[1] , package=driver[0])
		# self._mailer = mailer(params)
		self._mailer = Mailgun(params)

		self._client = gocardless_pro.Client(
			access_token = gc["token"],
			environment = gc["environment"]
		)

		self._limit = limit
		self._calculateDateLimit()

	def _calculateDateLimit(self) :
		today = datetime.datetime.today()

		if self._limit == "week" :
			l = (today - datetime.timedelta(weeks=1))

		elif self._limit == "month" :
			l = (today - datetime.timedelta(days=31))

		elif self._limit == "year" :
			l = (today - datetime.timedelta(weeks=52))

		elif self._limit == "finyear" :
			year = (today.year) if today.month > 4 else (today.year - 1)
			l = datetime.datetime(year, 4, 1, 0, 0, 0)

		elif self._limit == "all" :
			# So we don't have to check anywhere else
			l = datetime.datetime(1970, 1, 1, 0, 0, 0)
		else :
			raise ValueError("Incorrect limit specified")

		self._ldate = l.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

	def _fetchPayments(self, after = False) :
		# A 'payment' is the transfer of money from a customer to GoCardless

		params = {
			"status" : "paid_out",
			"limit"  : 500
		}

		if after :
			params["after"] = after

		payments = self._client.payments.list(params = params)

		for p in payments.records :
			self._payments[p.id] = {
				"payment_id"           : p.id,
				"payment_amount_gross" : round((p.amount / 100), 2),
				"payment_amount_net"   : self._calculateNet(p.amount),
				"payment_description"  : p.description
			}

		if payments.after :
			self._fetchPayments(payments.after)

	def _fetchPayouts(self, after = False) :
		# A 'payout' is a transfer of money from GoCardless to the account
		# Payouts consist of many payments (hence the need to reconcile these)

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
					self._payouts.append({
						"payout_id"        : p.id,
						"payout_date"      : p.arrival_date,
						"payout_reference" : p.reference,
						"payment_id"       : i.links.payment
					})

		if payouts.after :
			self._fetchPayouts(payouts.after)

	def _matchPayoutItemsWithPayments(self) :
		for p in self._payouts :
			try :
				payment = self._payments[p["payment_id"]]
				self._matched.append({ **payment, **p })
			except (KeyError) :
				exit("Missing Payment!") # This shouldn't happen!

	def _parseDescription(self, description) :
		pass

	def _calculateNet(self, amount) :
		# Fees are 2.95% if over £15, or (1.95% + 15p) if under
		amount = amount / 100
		if amount < 15 :
			fee = (0.0195 * amount) + 0.15
		else :
			fee = (0.0295 * amount)

		return round((amount - fee), 2)

	def reconcile(self) :
		self._fetchPayouts()
		self._fetchPayments()
		self._matchPayoutItemsWithPayments()

	def export(self) :
		pass

	def send(self) :
		if(not self.exported) :
			self.export()

		self._mailer.subject("GoCardless Payment Reconciliation")
		self._mailer.to(self._mail["to"])
		self._mailer.sender(self._mail["from"])
		# self._mailer.attach(self.exported)
		self._mailer.message("Test of the reconciler")
		self._mailer.send()

	def file(self) :
		return self.exported["path"]

	def counts(self) :
		print("Payouts: {}\nPayments: {}\nMatched: {}".format(
			len(self._payouts),
			len(self._payments),
			len(self._matched)
		))
