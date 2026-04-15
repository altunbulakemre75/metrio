"""Haftalık PDF raporu üret ve e-posta ile gönder."""
import sys
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from config import settings
from notifications.email import EmailSender, default_subject, format_email_body
from reports.builder import build_weekly_report
from storage.database import connect, init_schema


def main() -> int:
    try:
        conn = connect(settings.database_path)
        init_schema(conn)
    except Exception as e:
        print(f"❌ Veritabanı açılamadı: {e}")
        return 1

    recipients = [r for r in settings.email_recipients.split(",") if r.strip()]
    sender = EmailSender(
        smtp_host=settings.smtp_host,
        smtp_port=settings.smtp_port,
        smtp_user=settings.smtp_user,
        smtp_password=settings.smtp_password,
        email_from=settings.email_from,
        recipients=recipients,
        enabled=settings.email_enabled,
    )

    if not sender.enabled:
        print("ℹ️  EMAIL_ENABLED=false veya kredensiyel eksik. Çıkılıyor.")
        return 0

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"metrio_{datetime.now():%Y-%m-%d}.pdf"
        try:
            build_weekly_report(conn, output_path=pdf_path, days=7)
        except Exception as e:
            print(f"❌ PDF üretilemedi: {e}")
            return 1

        body = format_email_body(conn, days=7)
        subject = default_subject()
        success = sender.send(subject, body, attachment_path=pdf_path)

    if success:
        print(f"✅ Rapor {len(recipients)} alıcıya gönderildi.")
        return 0
    print("❌ Mail gönderilemedi (log dosyasına bak).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
