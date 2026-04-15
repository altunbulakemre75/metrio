"""Metrio — Günlük scraping pipeline'ı."""

import sys
import time
import traceback
import uuid
from datetime import datetime

from analysis.anomaly import detect_anomalies
from config import settings
from notifications.telegram import TelegramNotifier
from scrapers.base import BaseScraper
from scrapers.trendyol import TrendyolScraper
from storage.database import connect, init_schema, save_snapshot, start_run, finish_run
from utils.logger import get_logger

log = get_logger("pipeline")


_DEFAULT_CATEGORIES = [
    {
        "platform": "trendyol",
        "name": "kozmetik",
        "url": "https://www.trendyol.com/kozmetik-x-c89",
    },
]


def run_pipeline(
    scraper: BaseScraper,
    category_url: str,
    category_name: str,
    max_products: int = 500,
) -> dict:
    """Tek bir kategori için uçtan uca çalışır. run_stats sözlüğü döner."""
    run_id = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}"
    started_at = datetime.now()
    conn = connect(settings.database_path)
    init_schema(conn)

    start_run(conn, run_id=run_id, platform="trendyol", category=category_name, started_at=started_at)

    products_found = 0
    products_saved = 0
    products_failed = 0
    status = "success"
    error_message = None

    t0 = time.monotonic()
    try:
        log.info(f"Çekim başladı: {category_url}")
        snapshots = scraper.fetch_category(category_url, max_products=max_products)
        products_found = len(snapshots)
        log.info(f"{products_found} ürün tespit edildi")

        for snap in snapshots:
            try:
                save_snapshot(conn, snap)
                products_saved += 1
            except Exception as e:
                products_failed += 1
                log.warning(f"Snapshot kaydedilemedi (id={snap.platform_product_id}): {e}")

        if products_failed > 0 and products_saved > 0:
            status = "partial"
        elif products_saved == 0:
            status = "failed"
            error_message = "Hiçbir ürün kaydedilemedi"

    except Exception as e:
        status = "failed"
        error_message = str(e)
        log.error(f"Pipeline çöktü: {e}\n{traceback.format_exc()}")
    finally:
        try:
            scraper.close()
        except Exception as e:
            log.warning(f"Scraper kapatılırken hata: {e}")

        finished_at = datetime.now()
        duration = int(time.monotonic() - t0)

        finish_run(
            conn,
            run_id=run_id,
            status=status,
            products_found=products_found,
            products_saved=products_saved,
            products_failed=products_failed,
            finished_at=finished_at,
            duration_seconds=duration,
            error_message=error_message,
        )
        # In-memory test fixture aynı connection'ı tekrar kullanır, kapatma.
        # Real usage'da connect() her çağrıda yeni connection döner.

    log.info(f"Çekim tamamlandı ({status}): {products_saved} kaydedildi, {products_failed} hata, {duration}s")

    return {
        "run_id": run_id,
        "status": status,
        "products_found": products_found,
        "products_saved": products_saved,
        "products_failed": products_failed,
        "duration_seconds": duration,
        "error_message": error_message,
    }


def _combine_stats(all_stats: list[dict]) -> dict:
    """Birden çok kategorinin istatistiklerini tek özete indir."""
    if not all_stats:
        return {
            "status": "failed", "products_saved": 0, "duration_seconds": 0,
            "error_message": "Hiç kategori çalıştırılmadı",
        }
    saved = sum(s["products_saved"] for s in all_stats)
    duration = sum(s["duration_seconds"] for s in all_stats)
    any_failed = any(s["status"] == "failed" for s in all_stats)
    if any_failed and saved == 0:
        status = "failed"
    elif any_failed:
        status = "partial"
    else:
        status = "success"
    error = next((s["error_message"] for s in all_stats if s["error_message"]), None)
    return {
        "status": status,
        "products_saved": saved,
        "duration_seconds": duration,
        "error_message": error,
    }


def main() -> int:
    """CLI giriş noktası. Default kategori listesini çalıştırır."""
    overall_status = 0
    all_stats = []
    for cat in _DEFAULT_CATEGORIES:
        scraper = TrendyolScraper()
        stats = run_pipeline(
            scraper=scraper,
            category_url=cat["url"],
            category_name=cat["name"],
            max_products=settings.scraper_max_products,
        )
        all_stats.append(stats)
        if stats["status"] == "failed":
            overall_status = 1

    try:
        conn = connect(settings.database_path)
        init_schema(conn)
        anomalies = detect_anomalies(conn, threshold_percent=settings.telegram_threshold)
        combined_stats = _combine_stats(all_stats)
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
            enabled=settings.telegram_enabled,
        )
        notifier.notify_run(combined_stats, anomalies)
    except Exception as e:
        log.warning(f"Telegram bildirimi başarısız: {e}")

    return overall_status


if __name__ == "__main__":
    sys.exit(main())
