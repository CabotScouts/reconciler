import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from reconciler.mail import MailDriver
from reconciler.errors import ReconcilerMailerError


class SMTP(MailDriver):

    hostname = None
    port = None
    username = None
    password = None
    ssl = None

    def __init__(self, parameters):
        self.hostname = parameters.get("hostname", None)
        self.port = parameters.get("port", 25)
        self.username = parameters.get("username", None)
        self.password = parameters.get("password", None)
        self.ssl = parameters.get("ssl", False)

        if not self.hostname or not self.username or not self.password:
            raise ReconcilerMailerError("Required SMTP parameter is missing")

    def _parseAddressList(self, addresses):
        if isinstance(addresses, list):
            return ", ".join(addresses)

        else:
            return addresses

    def _send(self):
        mail = MIMEMultipart()
        mail["From"] = self.sendFrom
        mail["Subject"] = self.subject

        if self.sendTo:
            mail["To"] = self._parseAddressList(self.sendTo)

        if self.sendCC:
            mail["Cc"] = self._parseAddressList(self.sendCC)

        if self.sendBCC:
            mail["Bcc"] = self._parseAddressList(self.sendBCC)

        mail.attach(MIMEText(self.plainText, "plain"))

        if self.attachments:
            for f in self.attachments:
                with open(f, "rb") as attachment:
                    mime = MIMEBase("application", "octet-stream")
                    mime.set_payload(attachment.read())
                    encoders.encode_base64(mime)

                    mime.add_header(
                        "Content-Disposition", "attachment; filename={}".format(f)
                    )

                    mail.attach(mime)

        with smtplib.SMTP(self.hostname, self.port) as smtp:
            if self.ssl:
                smtp.starttls()

            smtp.login(self.username, self.password)
            smtp.send_message(mail)
