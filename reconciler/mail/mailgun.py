import requests
from reconciler.mail import MailDriver

class Mailgun (MailDriver) :

    api      = None
    key      = None
    domain   = None

    def __init__(self, options) :
        self.api      = options["api"]
        self.key      = options["key"]
        self.domain   = options["domain"]

        self.sender(options["from"])

    def endpoint(self, endpoint) :
        url = "https://{}/v3/{}/{}".format(self.api, self.domain, endpoint)
        return url

    def _send(self) :
        auth = ("api", self.key)

        files = [
            ("attachment", (f, open(f, 'rb'))) for f in self.attachments
        ]

        data = {
            "from"    : self.sendFrom,
            "to"      : self.sendTo,
            "cc"      : self.sendCC,
            "bcc"     : self.sendBCC,
            "subject" : self.subject,
            "text"    : self.plainText
        }

        send = requests.post(
            self.endpoint("messages"),
            auth=auth,
            files=files,
            data=data
        )

        if send.status_code != 200 :
            error = "{}: {}".format(send.status_code, send.error) if send.error else send.status_code
            raise HTTPError("Mailgun API Error - {}".format(error))
