from pathlib import Path
from unittest.mock import MagicMock, patch

from notifications.email import EmailSender


def _sender(**overrides):
    defaults = dict(
        smtp_host="smtp.test", smtp_port=587,
        smtp_user="user@test", smtp_password="pass",
        email_from="user@test", recipients=["a@x.com", "b@x.com"],
        enabled=True,
    )
    defaults.update(overrides)
    return EmailSender(**defaults)


def test_disabled_sender_does_not_call_smtp():
    sender = _sender(enabled=False)
    with patch("notifications.email.smtplib.SMTP") as mock_smtp:
        result = sender.send("subject", "body")
    assert result is False
    assert mock_smtp.call_count == 0


def test_missing_credentials_disables():
    sender = _sender(smtp_password="")
    with patch("notifications.email.smtplib.SMTP") as mock_smtp:
        result = sender.send("subject", "body")
    assert result is False
    assert mock_smtp.call_count == 0


def test_missing_recipients_disables():
    sender = _sender(recipients=[])
    with patch("notifications.email.smtplib.SMTP") as mock_smtp:
        result = sender.send("subject", "body")
    assert result is False
    assert mock_smtp.call_count == 0


def test_send_uses_starttls_login_send_message():
    sender = _sender()
    with patch("notifications.email.smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = sender.send("Konu", "Gövde")

    assert result is True
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once_with("user@test", "pass")
    mock_smtp.send_message.assert_called_once()
    sent_msg = mock_smtp.send_message.call_args.args[0]
    assert sent_msg["Subject"] == "Konu"
    assert "a@x.com" in sent_msg["To"]
    assert "b@x.com" in sent_msg["To"]


def test_send_attaches_pdf(tmp_path: Path):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake pdf content")

    sender = _sender()
    with patch("notifications.email.smtplib.SMTP") as mock_smtp_class:
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        sender.send("Konu", "Gövde", attachment_path=pdf)

    sent_msg = mock_smtp.send_message.call_args.args[0]
    # EmailMessage.iter_attachments only yields the attachment
    attachments = list(sent_msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "test.pdf"


def test_send_tolerates_smtp_errors():
    sender = _sender()
    with patch("notifications.email.smtplib.SMTP", side_effect=OSError("no net")):
        result = sender.send("Konu", "Gövde")
    assert result is False
