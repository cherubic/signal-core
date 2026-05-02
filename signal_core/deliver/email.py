import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .base import BaseDeliverer
from .formatter import format_html, format_text

logger = logging.getLogger(__name__)


class EmailDeliverer(BaseDeliverer):
    def send(self, digest: dict) -> None:
        host = os.environ["EMAIL_SMTP_HOST"]
        port = int(os.environ.get("EMAIL_SMTP_PORT", "587"))
        user = os.environ["EMAIL_SMTP_USER"]
        password = os.environ["EMAIL_SMTP_PASS"]
        to = os.environ["EMAIL_TO"]
        subject = f"Signal Daily · {digest['date']}"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.attach(MIMEText(format_text(digest), "plain", "utf-8"))
        msg.attach(MIMEText(format_html(digest), "html", "utf-8"))

        with smtplib.SMTP(host, port) as server:  # uses STARTTLS (port 587); SMTP_SSL not supported
            server.starttls()
            server.login(user, password)
            server.sendmail(user, to, msg.as_string())
        logger.info("Email sent to %s", to)
