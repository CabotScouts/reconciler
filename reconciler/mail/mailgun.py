import requests

from reconciler.mail import MailDriver
from reconciler.errors import ReconcilerMailerError


class Mailgun(MailDriver):

    api = None
    key = None
    domain = None

    def __init__(self, options):
        self.api = options.get("api", None)
        self.key = options.get("key", None)
        self.domain = options.get("domain", None)

        if not self.api or not self.key or not self.domain:
            raise ReconcilerMailerError("Required Mailgun parameter is missing")

    def endpoint(self, endpoint):
        return f"https://{self.api}/v3/{self.domain}/{endpoint}"

    def _send(self):
        auth = ("api", self.key)

        files = [("attachment", (f, open(f, "rb"))) for f in self.attachments]

        data = {
            "from": self.sendFrom,
            "to": self.sendTo,
            "cc": self.sendCC,
            "bcc": self.sendBCC,
            "subject": self.subject,
            "text": self.plainText,
        }

        send = requests.post(
            self.endpoint("messages"), auth=auth, files=files, data=data
        )

        if send.status_code != 200:
            error = (
                f"{send.status_code}: {send.error}" if send.error else send.status_code
            )
            raise ReconcilerMailerError(f"Mailgun API Error - {error}")
