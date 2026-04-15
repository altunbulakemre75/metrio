"""Haftalık PDF rapor üretme CLI."""
import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

from config import settings
from reports.builder import build_weekly_report
from storage.database import connect, init_schema


def main() -> int:
    parser = argparse.ArgumentParser(description="Haftalık PDF rapor üret.")
    parser.add_argument("--days", type=int, default=7, help="Lookback penceresi (gün)")
    parser.add_argument("--output", type=Path, default=Path("reports"), help="Çıktı dizini")
    parser.add_argument("--category", type=str, default=None, help="Kategori filtresi (şimdilik bilgi amaçlı)")
    args = parser.parse_args()

    try:
        conn = connect(settings.database_path)
        init_schema(conn)
    except Exception as e:
        print(f"❌ Veritabanı açılamadı: {e}")
        return 1

    filename = f"metrio_{datetime.now():%Y-%m-%d}.pdf"
    output_path = args.output / filename

    try:
        build_weekly_report(conn, output_path=output_path, days=args.days)
    except Exception as e:
        print(f"❌ Rapor üretilemedi: {e}")
        return 1

    print(f"✅ Rapor oluşturuldu: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
