import importlib
from reconciler.mail import drivers

from reconciler.mail.mailgun import Mailgun

import gocardless_pro

class Reconciler :

	_mail     = None # Parameters used for sending result by mail
	_mailer   = None # Mail driver class
	_client   = None # GoCardless client

	_payouts  = [] # Returned list of payouts
	_payments = [] # Returned list of payments
	_matched  = [] # Payouts matched to payments

	_exported = None # Exported xlsx file of matches

	def __init__(self, gc, params) :
		self._mail = params

		driver = drivers[params["driver"]]
		# mailer = importlib.import_module(driver[1] , package=driver[0])
		# self._mailer = mailer(params)
		self._mailer = Mailgun(params)

		self._client = gocardless_pro.Client(
			access_token = gc["token"],
			environment = gc["environment"]
		)

	def _fetchPayouts(self) :
		# A 'payout' is a transfer of money from GoCardless to the account
		# Payouts consist of many payments (hence the need to reconcile these)

		payouts = self._client.payouts.list(params = {
			"status"         : "paid",
			"limit"          : 100
			# "created_at[gt]" :
		}).records

		for p in payouts :
			self._payouts.append({
				"id"        : p.id,
				"date"      : p.arrival_date,
				"reference" : p.reference
			})

	def _fetchPayments(self) :
		# A 'payment' is the transfer of money from a customer to GoCardless
		# For each payout we need to fetch the payout_items it's made up of,
		# identify which of these are payments, then find those payments

		for m in self._payouts :
			payments = self._client.payout_items.list(params = {
				"payout" : m["id"]
			}).records

			for n in payments :
				if n.type == "payment_paid_out" :
					payment = self._client.payments.get(n.links.payment)
					self._payments.append({
						"payout_id"           : m["id"],
						"payout_date"         : m["date"],
						"payout_reference"    : m["reference"],
						"payment_id"          : payment.id,
						"payment_amount"      : (payment.amount / 100),
						"payment_description" : payment.description
					})

	def _parseDescription(self, description) :
		pass

	def reconcile(self) :
		self._fetchPayouts()
		self._fetchPayments()

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
