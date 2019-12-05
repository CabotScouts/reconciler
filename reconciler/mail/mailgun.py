import requests
from reconciler.mail import Mail

class Mailgun(Mail) :

    api      = None
    key      = None
    domain   = None

    def __init__(self, options) :
        self.api      = options["api"]
        self.key      = options["key"]
        self.domain   = options["domain"]
        self.sendFrom = options["from"]

    def endpoint(self, endpoint) :
        url = "https://{}/{}/{}".format(self.api, self.domain, endpoint)
        return url

    def _send(self) :
        auth = ("api", self.key)

        files = [
            ("attachment", (f["name"], open(f["path"], rb).read)) for f in self.attachments
        ]

        for addr in self.sendTo :
            data = {
                "from"    : self.sendFrom,
                "to"      : addr,
                "subject" : self.subject,
                "text"    : self.plainText
            }

            send = requests.post(
                self.endpoint("messages"),
                auth=auth,
                files=files,
                data=data
            )
