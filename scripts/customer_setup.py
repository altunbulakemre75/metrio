"""Metrio — İnteraktif müşteri kurulum CLI.

Kullanım:
    python scripts/customer_setup.py                 # interaktif
    python scripts/customer_setup.py --non-interactive < input.json
    python scripts/customer_setup.py --non-interactive --input '{"slug":"acme",...}'

JSON şeması (non-interactive):
    {
        "slug": "acme",
        "company": "ACME Kozmetik",
        "email": "info@acme.com",
        "telegram_chat_id": "123456789",
        "telegram_bot_token": "",
        "smtp_user": "",
        "smtp_password": "",
        "categories": [
            "https://www.trendyol.com/kozmetik-x-c89",
            "https://www.trendyol.com/parfum-x-c105"
        ],
        "overwrite": false
    }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "scripts" / "templates" / "customer.env.template"

SLUG_RE = re.compile(r"^[a-z0-9-]+$")

_KNOWN_CATEGORY_TOKENS = [
    "kozmetik", "elektronik", "giyim", "ev-yasam", "kitap",
    "cep-telefonu", "parfum", "makyaj", "cilt-bakimi", "vitamin",
]


def infer_platform(url: str) -> str:
    url_l = url.lower()
    if "hepsiburada" in url_l:
        return "hepsiburada"
    if "amazon" in url_l:
        return "amazon"
    return "trendyol"


def infer_category_name(url: str) -> str:
    """URL'den kategori adını çıkar. main.py / scrapers'daki mantığın aynısı."""
    url_l = url.lower()
    for k in _KNOWN_CATEGORY_TOKENS:
        if k in url_l:
            return k
    # fallback: slug'dan son parçayı çek (örn .../something-x-c123 -> something)
    m = re.search(r"/([a-z0-9\-]+?)(?:-x-c\d+)?/?(?:\?|$)", url_l)
    if m:
        return m.group(1)
    return "unknown"


def validate_slug(slug: str) -> None:
    if not SLUG_RE.match(slug):
        raise ValueError(
            f"Geçersiz slug: {slug!r}. Sadece küçük harf, rakam ve tire (-) kullanılabilir."
        )


def render_env_template(ctx: dict[str, str]) -> str:
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    for key, val in ctx.items():
        text = text.replace("{{" + key + "}}", str(val))
    return text


def build_categories(urls: list[str]) -> list[dict[str, str]]:
    out = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        out.append({
            "platform": infer_platform(url),
            "name": infer_category_name(url),
            "url": url,
        })
    return out


def write_customer_files(
    slug: str,
    company: str,
    email: str,
    telegram_chat_id: str,
    telegram_bot_token: str,
    smtp_user: str,
    smtp_password: str,
    category_urls: list[str],
    overwrite: bool,
    stdout=sys.stdout,
) -> None:
    validate_slug(slug)

    customer_dir = REPO_ROOT / "config" / "customers" / slug
    data_dir = REPO_ROOT / "data" / slug
    env_path = customer_dir / ".env"
    categories_path = customer_dir / "categories.json"

    if customer_dir.exists() and not overwrite:
        raise FileExistsError(
            f"config/customers/{slug}/ zaten var. Üzerine yazmak için --overwrite kullan."
        )

    customer_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    env_content = render_env_template({
        "slug": slug,
        "telegram_chat_id": telegram_chat_id,
        "telegram_bot_token": telegram_bot_token,
        "email": email,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
    })
    env_path.write_text(env_content, encoding="utf-8")

    categories = build_categories(category_urls)
    categories_path.write_text(
        json.dumps(categories, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Müşteri metadata (fatura vb için faydalı)
    meta_path = customer_dir / "meta.json"
    meta_path.write_text(
        json.dumps({"slug": slug, "company": company, "email": email}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] {env_path.relative_to(REPO_ROOT)} olusturuldu", file=stdout)
    print(f"[OK] {categories_path.relative_to(REPO_ROOT)} olusturuldu ({len(categories)} kategori)", file=stdout)
    print(f"[OK] {data_dir.relative_to(REPO_ROOT)}/ dizini olusturuldu", file=stdout)
    print(f"Siradaki: python main.py --config config/customers/{slug}/.env", file=stdout)


def interactive_main() -> int:
    print("=== Metrio Musteri Kurulum ===")
    slug = input("Musteri kisa adi (slug, orn. acme): ").strip().lower()
    try:
        validate_slug(slug)
    except ValueError as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2

    overwrite = False
    customer_dir = REPO_ROOT / "config" / "customers" / slug
    if customer_dir.exists():
        resp = input(f"config/customers/{slug}/ zaten var. Uzerine yazilsin mi? (y/N): ").strip().lower()
        if resp != "y":
            print("Iptal edildi.")
            return 1
        overwrite = True

    company = input("Sirket adi: ").strip()
    email = input("Musteri e-postasi: ").strip()
    telegram_chat_id = input("Telegram chat_id: ").strip()
    telegram_bot_token = input("Telegram bot token (bos birakabilirsin, ortak bot kullanilir): ").strip()
    smtp_user = input("SMTP gonderici e-posta (bos: ortak hesap): ").strip()
    smtp_password = input("SMTP sifre (bos: ortak hesap): ").strip()

    print("Izlenecek kategori URL'leri (bos satir bitirir):")
    urls: list[str] = []
    while True:
        u = input(" > ").strip()
        if not u:
            break
        urls.append(u)

    if not urls:
        print("UYARI: Hic kategori verilmedi. Yine de devam ediliyor (main.py default listeyi kullanir).")

    try:
        write_customer_files(
            slug=slug, company=company, email=email,
            telegram_chat_id=telegram_chat_id,
            telegram_bot_token=telegram_bot_token,
            smtp_user=smtp_user, smtp_password=smtp_password,
            category_urls=urls, overwrite=overwrite,
        )
    except Exception as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    return 0


def non_interactive_main(payload: dict[str, Any]) -> int:
    try:
        write_customer_files(
            slug=payload["slug"],
            company=payload.get("company", ""),
            email=payload.get("email", ""),
            telegram_chat_id=payload.get("telegram_chat_id", ""),
            telegram_bot_token=payload.get("telegram_bot_token", ""),
            smtp_user=payload.get("smtp_user", ""),
            smtp_password=payload.get("smtp_password", ""),
            category_urls=payload.get("categories", []),
            overwrite=payload.get("overwrite", False),
        )
    except Exception as e:
        print(f"HATA: {e}", file=sys.stderr)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Metrio musteri kurulum CLI")
    parser.add_argument("--non-interactive", action="store_true",
                        help="JSON input'u stdin'den veya --input'tan oku")
    parser.add_argument("--input", help="JSON payload (string)")
    parser.add_argument("--overwrite", action="store_true",
                        help="Mevcut config/customers/{slug}/ varsa uzerine yaz")
    args = parser.parse_args()

    if args.non_interactive:
        raw = args.input if args.input else sys.stdin.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"HATA: JSON parse: {e}", file=sys.stderr)
            return 2
        if args.overwrite:
            payload["overwrite"] = True
        return non_interactive_main(payload)
    else:
        return interactive_main()


if __name__ == "__main__":
    sys.exit(main())
