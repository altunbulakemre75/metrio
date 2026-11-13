"""Fırsat paylaşımı: seç → kart üret → Telegram kanalı + Instagram → kaydet.

Kullanım:
    python -m deals.run              # günün fırsatlarını paylaş
    python -m deals.run --dry-run    # sadece kartları üret (data/deals/)
    python -m deals.run --reel       # kaydırmalı gönderi yerine Reels videosu (--dry-run ile önizleme)
    python -m deals.run --check      # Instagram / görsel reposu / Telegram kanalı ayarlarını dene
"""
import argparse
import io
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from functools import partial
from pathlib import Path

from PIL import Image

from deals.affiliate import AFFILIATE_REF, DISCLOSURE, LinkBudget, affiliate_links_used
from deals.brands import PREFERRED_BRANDS
from deals.card import load_fonts, render_cover, render_deal_card, render_outro
from deals.hosting import GitImageHost, HostingError, wait_until_live
from deals.images import fetch_product_image
from deals.instagram import InstagramClient, InstagramError, current_token
from deals.selector import Deal, select_deals
from deals.text import instagram_caption, telegram_caption, tiktok_mentions, video_caption
from deals.video import VideoError, render_reel
from storage.database import get_recently_posted_product_ids, record_posted_deals

_MIN_DEALS = 3
_TOKEN_STORE = Path("data/instagram_token.json")
_OUT_ROOT = Path("data/deals")


@dataclass(frozen=True)
class DealsConfig:
    page_name: str
    categories: list[str]
    per_post: int
    min_discount: float
    exclude_words: list[str]
    repeat_after: timedelta
    caption_footer: str
    hashtags: str
    font_dir: str
    category_caps: dict[str, int] = field(default_factory=dict)
    telegram_channel: str = ""
    special_days: dict[str, str] = field(default_factory=dict)  # "11-11" → "11.11"
    preferred_brands: tuple[str, ...] = ()
    # Telifli müzik API ile eklenemiyor: Reels Instagram'a otomatik atılmaz, video ve
    # açıklamalar yöneticiye gider, müzik uygulamadan eklenip elle paylaşılır.
    reel_manual: bool = False
    reel_music: str = ""
    affiliate_template: str = ""  # AFFILIATE_URL_TEMPLATE; boşsa düz ürün linki
    batch_suffix: str = ""  # kart klasörü adına eklenir ("-ekstra"): aynı dakikadaki çalışmalar çakışmasın


@dataclass
class RunResult:
    status: str  # no_deals | rendered | posted | partial | failed
    deals: list[Deal] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    media_id: str | None = None
    video: Path | None = None


def run_once(
    conn: sqlite3.Connection,
    cfg: DealsConfig,
    now: datetime,
    out_root: Path,
    *,
    host=None,
    instagram=None,
    telegram_send: Callable[[Path, str], bool] | None = None,
    notify_admin: Callable[[str], None] | None = None,
    image_fetcher: Callable[[str], Image.Image | None] = fetch_product_image,
    wait_live: Callable[[list[str]], bool] = wait_until_live,
    max_age: timedelta = timedelta(hours=36),
    reel: bool = False,
    video_maker: Callable[[list[Path], Path], Path] = render_reel,
    share_video: Callable[[Path, str], bool] | None = None,
    share_text: Callable[[str], None] | None = None,
    share_album: Callable[[list[Path], str], bool] | None = None,
) -> RunResult:
    def alert(text: str) -> None:
        if notify_admin:
            notify_admin(f"Fırsat sayfası: {text}")

    deals = select_deals(
        conn, cfg.categories, now, limit=cfg.per_post,
        exclude_ids=get_recently_posted_product_ids(conn, since=now - cfg.repeat_after),
        min_discount=cfg.min_discount, exclude_words=cfg.exclude_words, max_age=max_age,
        category_caps=cfg.category_caps, preferred_brands=cfg.preferred_brands,
    )
    if len(deals) < _MIN_DEALS:
        alert(f"yalnızca {len(deals)} fırsat bulundu, paylaşım yapılmadı. Gece taraması çalışıyor mu?")
        return RunResult("no_deals", deals)

    fonts = load_fonts(cfg.font_dir)
    label = cfg.special_days.get(now.strftime("%m-%d"), "")
    batch = out_root / (now.strftime("%Y%m%d-%H%M") + cfg.batch_suffix)
    cover = render_cover(deals, now, cfg.page_name, batch / "cover.jpg", fonts,
                         cta="" if reel else "Kaydır →",
                         title=f"{label.upper()} FIRSATLARI" if label else "")
    cards = [
        render_deal_card(d, image_fetcher(d.image_url), cfg.page_name, batch / f"{i}.jpg", fonts,
                         index=i if reel else None)
        for i, d in enumerate(deals, start=1)
    ]
    result = RunResult("rendered", deals, [cover, *cards])
    frames: list[Path] = []
    if reel:
        # Video en iyi fırsatla açılır (ilk saniyede kaydırılmasın), takip kartıyla biter.
        # Kapak yalnızca kaydırmalı gönderide kalır.
        frames = [*cards, render_outro(cfg.page_name, cfg.telegram_channel, batch / "outro.jpg",
                                       fonts)]
        try:
            result.video = video_maker(frames, batch / "reel.mp4")
        except VideoError as e:
            alert(f"Reels videosu üretilemedi, kaydırmalı gönderi atılıyor: {e}")
    if telegram_send is None and instagram is None:
        return result

    outcomes = []
    if telegram_send is not None:
        budget = LinkBudget(cfg.affiliate_template, affiliate_links_used(conn, now))
        sent = []
        for d, card in zip(deals, cards):
            url, is_affiliate = budget.link(d.product_url)
            if telegram_send(card, telegram_caption(d, url, DISCLOSURE if is_affiliate else "")):
                sent.append(d)
                record_posted_deals(conn, [d.product_id], "telegram",
                                    AFFILIATE_REF if is_affiliate else None, now)
        if not sent:
            alert("Telegram kanalına hiçbir fırsat gönderilemedi.")
        outcomes.append(bool(sent))

    manual = cfg.reel_manual and result.video is not None
    if instagram is not None and not manual:
        outcomes.append(_post_instagram(conn, cfg, now, deals, result, host, instagram,
                                        wait_live, alert))

    # TikTok'a (elle modda Instagram'a da) müzikli yüklemek için videoyu yöneticiye gönder.
    if result.video is not None and share_video is not None:
        if manual and share_text is not None:
            share_text(_manual_note(cfg.reel_music))
        if not share_video(result.video, video_caption(deals, now, cfg.telegram_channel,
                                                       cfg.hashtags, label, tiktok_mentions(deals))):
            alert("video yönetici sohbetine gönderilemedi; dosya: " + str(result.video))
        if share_album is not None:
            share_album(frames, "📸 TikTok fotoğraf modu: aynı kartlar. TikTok'ta 'Fotoğraf' "
                                "seçip aynı şarkı ve videodaki açıklamayla yükle.")
        if manual and share_text is not None:
            share_text(_instagram_caption(cfg, now, deals))

    if not outcomes:  # elle Reels modunda Telegram kanalı da yoksa hiçbir yere paylaşılmadı
        return result
    if all(outcomes):
        result.status = "posted"
    elif any(outcomes):
        result.status = "partial"
    else:
        result.status = "failed"
    return result


def _instagram_caption(cfg: DealsConfig, now: datetime, deals: list[Deal]) -> str:
    return instagram_caption(deals, now, cfg.caption_footer, cfg.hashtags,
                             cfg.special_days.get(now.strftime("%m-%d"), ""))


def _manual_note(music: str) -> str:
    lines = ["🎬 Reels hazır, Instagram ve TikTok'a sen paylaşıyorsun."]
    if music:
        lines.append(f"🎵 Müzik: {music} (uygulamanın müzik kütüphanesinden ekle)")
    lines.append("Videonun altındaki açıklama TikTok için, sonraki mesaj Instagram için.")
    return "\n".join(lines)


def _post_instagram(conn, cfg, now, deals, result, host, instagram, wait_live, alert) -> bool:
    caption = _instagram_caption(cfg, now, deals)
    try:
        if result.video is not None:
            result.media_id = instagram.publish_reel(result.video, caption)
        else:
            urls = host.publish(result.files, now)
            if not wait_live(urls):
                alert("görseller herkese açık adreste görünmedi, Instagram paylaşımı atlandı.")
                return False
            result.media_id = instagram.publish_carousel(urls, caption)
    except (HostingError, InstagramError) as e:
        alert(f"Instagram paylaşımı başarısız: {e}")
        return False
    record_posted_deals(conn, [d.product_id for d in deals], "instagram", result.media_id, now)
    return True


_EXTRA_PER_CATEGORY = 2


def extra_config(cfg: DealsConfig, categories: list[str]) -> DealsConfig:
    """Kozmetik dışı türler için ayrı video: kendi kategorileri, tür başına en fazla 2 ürün."""
    return replace(cfg, categories=list(categories),
                   category_caps={c: _EXTRA_PER_CATEGORY for c in categories},
                   batch_suffix="-ekstra")


def _config_from_settings(settings) -> DealsConfig:
    return DealsConfig(
        page_name=settings.deals_page_name,
        categories=settings.deals_category_list,
        per_post=settings.deals_per_post,
        min_discount=settings.deals_min_discount,
        exclude_words=settings.deals_exclude_word_list,
        repeat_after=timedelta(days=settings.deals_repeat_after_days),
        caption_footer=settings.deals_caption_footer,
        hashtags=settings.deals_hashtags,
        font_dir=settings.deals_font_dir,
        category_caps=settings.deals_category_cap_map,
        telegram_channel=settings.telegram_channel_id,
        special_days=settings.deals_special_day_map,
        preferred_brands=PREFERRED_BRANDS,
        reel_manual=settings.instagram_reel_manual,
        affiliate_template=settings.affiliate_url_template,
        reel_music=settings.deals_reel_music,
    )


def _instagram_from_settings(settings, now):
    if not settings.instagram_enabled:
        return None, None
    missing = [name for name, value in [
        ("INSTAGRAM_USER_ID", settings.instagram_user_id),
        ("IMAGE_HOST_REPO_DIR", settings.image_host_repo_dir),
        ("IMAGE_HOST_BASE_URL", settings.image_host_base_url),
    ] if not value]
    if missing:
        raise InstagramError(f"eksik ayar: {', '.join(missing)}")
    token = current_token(_TOKEN_STORE, settings.instagram_access_token, now)
    client = InstagramClient(settings.instagram_user_id, token, settings.instagram_api_version)
    host = GitImageHost(settings.image_host_repo_dir, settings.image_host_base_url)
    return client, host


def check_setup(settings, now: datetime) -> list[str]:
    """Kurulum adımlarını tek tek dener; okunabilir satırlar döner."""
    import requests
    lines = []

    if settings.telegram_bot_token and settings.telegram_channel_id:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/getChat",
                params={"chat_id": settings.telegram_channel_id}, timeout=15,
            )
            body = resp.json()
            if body.get("ok"):
                lines.append(f"OK    Telegram kanalı: {body['result'].get('title')}")
            else:
                lines.append(f"HATA  Telegram kanalı: {body.get('description')}")
        except requests.exceptions.RequestException as e:
            lines.append(f"HATA  Telegram kanalı: {e}")
    else:
        lines.append("YOK   Telegram kanalı ayarlı değil (TELEGRAM_CHANNEL_ID)")

    if not settings.instagram_enabled:
        lines.append("YOK   Instagram kapalı (INSTAGRAM_ENABLED=false)")
        return lines
    try:
        client, host = _instagram_from_settings(settings, now)
        assert client is not None and host is not None
        account = client.account()
        lines.append(f"OK    Instagram hesabı: @{account.get('username')} (id {account.get('user_id')})")
        if str(account.get("user_id")) != str(settings.instagram_user_id):
            lines.append(f"UYARI INSTAGRAM_USER_ID {settings.instagram_user_id}, "
                         f"hesabın id'si {account.get('user_id')}")
        lines.append(f"OK    Paylaşım limiti: {client.publishing_limit().get('data')}")
        lines.append(f"OK    Görsel reposu: {host.remote_url()}")
    except (InstagramError, HostingError, requests.exceptions.RequestException) as e:
        lines.append(f"HATA  Instagram kurulumu: {e}")
    return lines


def main(argv: list[str] | None = None) -> int:
    from config import settings
    from notifications.telegram import TelegramNotifier, send_media_group, send_photo, send_video
    from storage.database import connect, init_schema
    from utils.logger import get_logger

    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    log = get_logger("deals")

    parser = argparse.ArgumentParser(description="Kozmetik fırsatlarını paylaş")
    parser.add_argument("--dry-run", action="store_true", help="Sadece kartları üret")
    parser.add_argument("--check", action="store_true", help="Kurulumu dene, paylaşım yapma")
    parser.add_argument("--reel", action="store_true",
                        help="Kaydırmalı gönderi yerine Reels videosu (INSTAGRAM_REEL_HOURS saatlerinde kendiliğinden)")
    parser.add_argument("--extra", action="store_true",
                        help="Kozmetik dışı türler (DEALS_EXTRA_CATEGORIES) için ayrı Reels videosu")
    parser.add_argument("--max-age-hours", type=int, default=36,
                        help="Bu kadar saatten eski fiyatları kullanma (varsayılan 36)")
    args = parser.parse_args(argv)
    now = datetime.now()

    if args.check:
        for line in check_setup(settings, now):
            print(line)
        return 0

    admin = TelegramNotifier(settings.telegram_bot_token, settings.telegram_chat_id,
                             settings.telegram_enabled)
    conn = connect(settings.database_path)
    init_schema(conn)

    telegram_send = instagram = host = share_video = share_album = None
    if not args.dry_run:
        if settings.telegram_bot_token and settings.telegram_chat_id:
            share_video = partial(send_video, settings.telegram_bot_token, settings.telegram_chat_id)
            share_album = partial(send_media_group, settings.telegram_bot_token,
                                  settings.telegram_chat_id)
        if settings.telegram_bot_token and settings.telegram_channel_id:
            telegram_send = partial(send_photo, settings.telegram_bot_token,
                                    settings.telegram_channel_id)
        try:
            instagram, host = _instagram_from_settings(settings, now)
        except InstagramError as e:
            log.error(f"Instagram ayarı hatalı: {e}")
            admin.send_text(f"Fırsat sayfası: Instagram ayarı hatalı: {e}")
        if telegram_send is None and instagram is None:
            log.warning("Hiçbir kanal ayarlı değil; sadece kartlar üretilecek.")

    cfg = _config_from_settings(settings)
    if args.extra:
        if not settings.deals_extra_category_list:
            print("DEALS_EXTRA_CATEGORIES boş; ekstra video için kategori yok.")
            return 1
        cfg = extra_config(cfg, settings.deals_extra_category_list)

    # Kanal yokken (kurulum sürerken) yöneticiye günde 3 kez uyarı gitmesin.
    has_channel = telegram_send is not None or instagram is not None
    result = run_once(
        conn, cfg, now, _OUT_ROOT,
        host=host, instagram=instagram, telegram_send=telegram_send,
        notify_admin=admin.send_text if has_channel else None,
        max_age=timedelta(hours=args.max_age_hours),
        reel=args.reel or args.extra or now.hour in settings.instagram_reel_hour_set,
        share_video=share_video,
        share_text=admin.send_text if share_video is not None else None,
        share_album=share_album,
    )
    log.info(f"Fırsat paylaşımı: {result.status}, {len(result.deals)} fırsat, "
             f"kartlar: {result.files[0].parent if result.files else '-'}"
             f"{', video: ' + str(result.video) if result.video else ''}")
    return 0 if result.status in ("posted", "rendered", "no_deals") else 1


if __name__ == "__main__":
    sys.exit(main())
