"""Telegram chat ID'yi bulmak için yardımcı.

Kullanım:
  1. BotFather'dan token al.
  2. .env dosyasına TELEGRAM_BOT_TOKEN=... ekle.
  3. Bota Telegram'dan herhangi bir mesaj gönder.
  4. python scripts/setup_telegram.py çalıştır.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import requests

from config import settings


def main() -> int:
    token = settings.telegram_bot_token
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN boş. Önce .env'ye ekle.")
        return 1

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = requests.get(url, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"❌ Bağlantı hatası: {e}")
        return 1

    data = response.json()
    if not data.get("ok"):
        print(f"❌ API hatası: {data}")
        return 1

    updates = data.get("result", [])
    if not updates:
        print("ℹ️  Henüz mesaj yok. Botuna Telegram'dan bir mesaj gönder, sonra tekrar çalıştır.")
        return 1

    chat_ids = {u["message"]["chat"]["id"] for u in updates if "message" in u}
    print("✅ Bulunan chat ID'ler:")
    for cid in chat_ids:
        print(f"   {cid}")
    print()
    print("Bu değeri .env dosyasına TELEGRAM_CHAT_ID=... olarak ekle.")
    print("TELEGRAM_ENABLED=true yapmayı unutma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
