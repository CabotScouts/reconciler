drivers = {
	"smtp"    : ("reconciler.mail.smtp", "SMTP"),
	"mailgun" : ("reconciler.mail", "mailgun.Mailgun")
}

class Mail :

	subject     = None
	sendTo      = None
	sendFrom    = None
	attachments = []
	plainText   = None

	def subject(self, subject) :
		self.subject = subject
		return self

	def to(self, to) :
		self.sendTo = to
		return self

	def sender(self, sender) :
		self.sendFrom = sender
		return self

	def message(self, message) :
		self.plainText = message
		return self

	def attach(self, pathToFile) :
		pass

	def send(self) :
		self._send()
		return self
