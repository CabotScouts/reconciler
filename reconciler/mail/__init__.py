drivers = {
    "smtp"    : ("reconciler.mail.smtp", "SMTP"),
    "mailgun" : ("reconciler.mail.mailgun", "Mailgun")
}

class Mail :

    subject     = None
    sendTo      = None
    sendCC      = None
    sendBCC     = None
    sendFrom    = None
    attachments = []
    plainText   = None

    def subject(self, subject) :
        self.subject = subject
        return self

    def to(self, to) :
        self.sendTo = to
        return self

    def cc(self, cc) :
        self.sendCC = cc
        return self

    def bcc(self, bcc) :
        self.sendBCC = bcc
        return self

    def sender(self, sender) :
        self.sendFrom = sender
        return self

    def message(self, message) :
        self.plainText = message
        return self

    def attach(self, filename) :
        self.attachments.append(filename)

    def send(self) :
        try :
            assert(isinstance(self.subject, str))
            assert(isinstance(self.sendFrom, str))
            assert(isinstance(self.plainText, str))

        except :
            raise ValueError("A required email field is either blank or the wrong type")

        if not (self.sendTo or self.sendCC or self.sendBCC) :
            raise ValueError("Some form of email recipient must be specified (either to, cc, or bcc)")

        self._send()
        return self
