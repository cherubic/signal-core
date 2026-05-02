import os
from unittest.mock import patch, MagicMock
from tests.conftest import make_summarized_item
from signal_core.deliver.email import EmailDeliverer
from signal_core.deliver.formatter import format_digest
from datetime import date


@patch.dict(os.environ, {
    "EMAIL_SMTP_HOST": "smtp.example.com",
    "EMAIL_SMTP_PORT": "587",
    "EMAIL_SMTP_USER": "user@example.com",
    "EMAIL_SMTP_PASS": "secret",
    "EMAIL_TO": "me@example.com",
})
def test_email_deliverer_sends_message():
    items = [make_summarized_item(url=f"https://ex.com/{i}") for i in range(3)]
    digest = format_digest(items, date(2026, 5, 2))

    with patch("signal_core.deliver.email.smtplib.SMTP") as MockSMTP:
        mock_server = MagicMock()
        MockSMTP.return_value.__enter__.return_value = mock_server

        deliverer = EmailDeliverer()
        deliverer.send(digest)

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.sendmail.assert_called_once()
        args = mock_server.sendmail.call_args[0]
        assert args[0] == "user@example.com"
        assert args[1] == "me@example.com"
        raw_msg = mock_server.sendmail.call_args[0][2]
        assert "Signal_Daily" in raw_msg  # Subject header uses RFC 2047 quoted-printable encoding
        assert "2026-05-02" in raw_msg
