"""SMTP ile haftalık rapor e-posta gönderimi."""
import logging
import smtplib
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

from analysis.anomaly import detect_anomalies
from analysis.price_changes import top_movers
from analysis.queries import get_latest_snapshots_df

log = logging.getLogger(__name__)


def format_email_body(conn, days: int = 7) -> str:
    """Plain text mail gövdesi üret."""
    try:
        df = get_latest_snapshots_df(conn)
        movers = top_movers(conn, days=days, direction="both", limit=3)
        anomalies = detect_anomalies(conn, threshold_percent=0.20)
    except Exception:
        df = None
        movers, anomalies = [], []

    lines = ["Merhaba,", "", "Haftalık fiyat izleme raporunuz ektedir.", ""]

    if df is None or df.empty:
        lines.extend(["Bu dönemde takip edilen veri yok.", ""])
    else:
        lines.append(f"Bu hafta:")
        lines.append(f"- {len(df)} ürün takip edildi")
        lines.append(f"- {len(anomalies)} anomali tespit edildi")
        if movers:
            m = movers[0]
            pct = m.change_percent * 100
            brand = m.brand or ""
            lines.append(f"- En büyük fırsat: {brand} {m.name[:50]} {pct:+.0f}%")
        lines.append("")

    lines.extend(["Detaylar PDF ekinde.", "", "— Metrio"])
    return "\n".join(lines)


class EmailSender:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        email_from: str,
        recipients: list[str],
        enabled: bool,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from or smtp_user
        self.recipients = [r.strip() for r in recipients if r.strip()]
        self.enabled = (
            enabled
            and bool(smtp_user)
            and bool(smtp_password)
            and bool(self.recipients)
        )

    def send(self, subject: str, body: str, attachment_path: Path | None = None) -> bool:
        if not self.enabled:
            log.info("Email devre dışı, gönderim atlandı.")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.email_from
        msg["To"] = ", ".join(self.recipients)
        msg.set_content(body)

        if attachment_path is not None:
            path = Path(attachment_path)
            if path.exists():
                data = path.read_bytes()
                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="pdf",
                    filename=path.name,
                )

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as smtp:
                smtp.starttls()
                smtp.login(self.smtp_user, self.smtp_password)
                smtp.send_message(msg)
            log.info(f"Mail {len(self.recipients)} alıcıya gönderildi.")
            return True
        except Exception as e:
            log.warning(f"Mail gönderilemedi: {e}")
            return False


def default_subject() -> str:
    return f"Metrio — Haftalık Rapor ({datetime.now():%Y-%m-%d})"
