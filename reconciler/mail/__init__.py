drivers = {
    "smtp": ("reconciler.mail.smtp", "SMTP"),
    "mailgun": ("reconciler.mail.mailgun", "Mailgun"),
}


class ReconcilerMailerError(Exception):
    # Something is wrong with the mailer
    pass


class MailDriver:

    subject = None
    sendTo = None
    sendCC = None
    sendBCC = None
    sendFrom = None
    attachments = []
    plainText = None

    def subject(self, subject):
        self.subject = subject
        return self

    def to(self, to):
        self.sendTo = to
        return self

    def cc(self, cc):
        self.sendCC = cc
        return self

    def bcc(self, bcc):
        self.sendBCC = bcc
        return self

    def sender(self, sender):
        self.sendFrom = sender
        return self

    def message(self, message):
        self.plainText = message
        return self

    def attach(self, filename):
        self.attachments.append(filename)

    def send(self):
        if (
            not isinstance(self.subject, str)
            or not isinstance(self.sendFrom, str)
            or not isinstance(self.plainText, str)
        ):
            raise ReconcilerMailerError(
                "A required email field is either blank or the wrong type"
            )

        if not (self.sendTo or self.sendCC or self.sendBCC):
            raise ReconcilerMailerError(
                "Some form of email recipient must be specified (either to, cc, or bcc)"
            )

        self._send()
        return self
