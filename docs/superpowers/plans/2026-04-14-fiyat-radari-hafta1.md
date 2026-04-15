# Metrio — Hafta 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular, TDD-tested Python pipeline that scrapes Trendyol's cosmetics category using Playwright, stores product data as a time-series in SQLite, and runs daily via Windows Task Scheduler.

**Architecture:** Modular scraper design with a `BaseScraper` abstract interface so new sites (Hepsiburada, Amazon) can be added later by implementing a single file. Two-table normalized schema separates stable product identity from time-series price snapshots. Decorator-based cross-cutting concerns (retry, rate limiting). Pure parser functions testable offline with fixtures; real browser only for end-to-end validation.

**Tech Stack:** Python 3.11+, Playwright (Chromium headless), SQLite, pydantic-settings, pytest, Python `logging` stdlib.

**Platform:** Windows 11, bash shell (use forward slashes in paths, Unix-style commands).

---

## File Structure

**Create:**
- `verimadenciligi/scrapers/__init__.py`
- `verimadenciligi/scrapers/base.py` — `BaseScraper` abstract class
- `verimadenciligi/scrapers/trendyol.py` — `TrendyolScraper` + parsers
- `verimadenciligi/storage/__init__.py`
- `verimadenciligi/storage/models.py` — `ProductSnapshot` dataclass
- `verimadenciligi/storage/database.py` — connection + CRUD
- `verimadenciligi/storage/migrations/001_initial.sql` — schema
- `verimadenciligi/utils/__init__.py`
- `verimadenciligi/utils/logger.py` — logger config
- `verimadenciligi/utils/retry.py` — retry decorator
- `verimadenciligi/utils/rate_limiter.py` — rate limit decorator
- `verimadenciligi/tests/__init__.py`
- `verimadenciligi/tests/unit/` — pure function tests
- `verimadenciligi/tests/integration/` — offline fixture tests
- `verimadenciligi/tests/e2e/` — real Trendyol tests
- `verimadenciligi/tests/fixtures/` — sample HTML files
- `verimadenciligi/config.py` — pydantic-settings config
- `verimadenciligi/main.py` — pipeline entry point
- `verimadenciligi/requirements.txt`
- `verimadenciligi/.gitignore`
- `verimadenciligi/.env.example`
- `verimadenciligi/README.md`
- `verimadenciligi/pytest.ini`

**Directories (not committed, in .gitignore):**
- `verimadenciligi/data/` — SQLite database
- `verimadenciligi/logs/` — log files
- `verimadenciligi/.venv/` — virtual environment

---

## Task 1: Project Bootstrap

**Files:**
- Create: `.gitignore`, `.env.example`, `requirements.txt`, `README.md`, `pytest.ini`
- Create directories: `scrapers/`, `storage/`, `storage/migrations/`, `utils/`, `tests/unit/`, `tests/integration/`, `tests/e2e/`, `tests/fixtures/`, `analysis/`, `reporting/`, `notifications/`, `dashboard/`, `data/`, `logs/`

- [ ] **Step 1: Initialize git repository**

Run from `c:/Users/altun/Desktop/Yeni klasör/verimadenciligi`:
```bash
git init
git branch -m main
```
Expected: "Initialized empty Git repository"

- [ ] **Step 2: Create directory structure**

```bash
mkdir -p scrapers storage/migrations utils analysis reporting notifications dashboard data logs
mkdir -p tests/unit tests/integration tests/e2e tests/fixtures/trendyol_edge_cases
```

- [ ] **Step 3: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
.venv/
venv/
*.egg-info/

# Environment
.env

# Data & Logs
data/*.db
data/*.db-journal
logs/*.log
logs/*.log.*

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Playwright
playwright-report/
test-results/
```

- [ ] **Step 4: Create `.env.example`**

```
# Application
APP_ENV=development
LOG_LEVEL=INFO

# Database
DATABASE_PATH=data/metrio.db

# Scraper
SCRAPER_MAX_PRODUCTS=500
SCRAPER_HEADLESS=true
SCRAPER_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36
SCRAPER_REQUESTS_PER_SECOND=1.0

# Telegram (Week 2 — leave empty for now)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

- [ ] **Step 5: Create `requirements.txt`**

```
playwright==1.48.0
beautifulsoup4==4.12.3
lxml==5.3.0
pydantic==2.9.2
pydantic-settings==2.6.1
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 6: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
markers =
    e2e: tests that hit real external services (deselect with '-m "not e2e"')
addopts = -v --strict-markers -m "not e2e"
asyncio_mode = auto
```

- [ ] **Step 7: Create `README.md`**

```markdown
# Metrio

E-ticaret fiyat istihbaratı sistemi. Trendyol, Hepsiburada ve diğer platformlardan rakip fiyat takibi yapar.

## Kurulum

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

## Çalıştırma

```bash
python main.py
```

## Test

```bash
pytest                  # Unit + integration testleri
pytest -m e2e           # Sadece E2E testler (gerçek Trendyol)
```

## Mimari

Detaylı tasarım için: `docs/superpowers/specs/2026-04-14-fiyat-radari-design.md`
```

- [ ] **Step 8: Create empty `__init__.py` files**

```bash
touch scrapers/__init__.py storage/__init__.py utils/__init__.py
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/e2e/__init__.py
```

- [ ] **Step 9: Create Python virtual environment and install**

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
playwright install chromium
```

Expected: Playwright downloads Chromium (~150MB), packages install without error.

- [ ] **Step 10: Verify test infrastructure works**

Run:
```bash
pytest --collect-only
```
Expected: `collected 0 items` (no tests yet, but pytest configured).

- [ ] **Step 11: Commit**

```bash
cp .env.example .env
git add .gitignore .env.example requirements.txt README.md pytest.ini
git add scrapers/ storage/ utils/ tests/ analysis/ reporting/ notifications/ dashboard/
git commit -m "chore: project bootstrap with folder structure and dependencies"
```

---

## Task 2: Config Module

**Files:**
- Create: `config.py`
- Test: `tests/unit/test_config.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_config.py`:
```python
import os
from config import Settings


def test_settings_loads_defaults(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_PATH", "data/test.db")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("SCRAPER_MAX_PRODUCTS", "100")
    monkeypatch.setenv("SCRAPER_HEADLESS", "true")
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")
    monkeypatch.setenv("SCRAPER_REQUESTS_PER_SECOND", "1.0")

    settings = Settings()

    assert settings.app_env == "development"
    assert settings.database_path == "data/test.db"
    assert settings.scraper_max_products == 100
    assert settings.scraper_requests_per_second == 1.0
    assert settings.scraper_headless is True


def test_settings_validates_log_level(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    monkeypatch.setenv("DATABASE_PATH", "data/test.db")
    monkeypatch.setenv("SCRAPER_USER_AGENT", "test-agent")

    import pytest
    with pytest.raises(Exception):
        Settings()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Implement `config.py`**

```python
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    database_path: str = "data/metrio.db"

    scraper_max_products: int = Field(default=500, gt=0)
    scraper_headless: bool = True
    scraper_user_agent: str
    scraper_requests_per_second: float = Field(default=1.0, gt=0)

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_config.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/unit/test_config.py
git commit -m "feat: add pydantic-validated config module"
```

---

## Task 3: Logger Utility

**Files:**
- Create: `utils/logger.py`
- Test: `tests/unit/test_logger.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_logger.py`:
```python
import logging
from utils.logger import get_logger


def test_logger_returns_named_logger():
    logger = get_logger("test_component")
    assert logger.name == "test_component"
    assert logger.level <= logging.INFO


def test_logger_emits_formatted_message(caplog):
    logger = get_logger("trendyol")
    with caplog.at_level(logging.INFO, logger="trendyol"):
        logger.info("Test mesaj")
    assert "Test mesaj" in caplog.text
    assert "trendyol" in caplog.text


def test_logger_reused_for_same_name():
    a = get_logger("same")
    b = get_logger("same")
    assert a is b
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_logger.py -v
```
Expected: `ModuleNotFoundError: No module named 'utils.logger'`

- [ ] **Step 3: Implement `utils/logger.py`**

```python
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "[%(asctime)s] %(levelname)-5s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def _configure_root():
    global _configured
    if _configured:
        return

    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_handler = TimedRotatingFileHandler(
        logs_dir / "scraper.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(name)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_logger.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add utils/logger.py tests/unit/test_logger.py
git commit -m "feat: add structured logger with daily rotation"
```

---

## Task 4: Retry Decorator

**Files:**
- Create: `utils/retry.py`
- Test: `tests/unit/test_retry.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_retry.py`:
```python
import pytest
from utils.retry import retry


def test_retry_succeeds_on_first_try():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        return "ok"

    assert work() == "ok"
    assert len(calls) == 1


def test_retry_succeeds_on_second_attempt():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("boom")
        return "ok"

    assert work() == "ok"
    assert len(calls) == 2


def test_retry_exhausts_attempts_and_reraises():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        raise ConnectionError("always fails")

    with pytest.raises(ConnectionError, match="always fails"):
        work()
    assert len(calls) == 3


def test_retry_does_not_catch_unspecified_exceptions():
    calls = []

    @retry(max_attempts=3, backoff_base=0, exceptions=(ConnectionError,))
    def work():
        calls.append(1)
        raise ValueError("not retriable")

    with pytest.raises(ValueError):
        work()
    assert len(calls) == 1


def test_retry_exponential_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    @retry(max_attempts=4, backoff_base=2)
    def work():
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        work()

    assert sleeps == [1, 2, 4]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_retry.py -v
```
Expected: `ModuleNotFoundError: No module named 'utils.retry'`

- [ ] **Step 3: Implement `utils/retry.py`**

```python
import functools
import time
from typing import Callable, Type

from utils.logger import get_logger

log = get_logger("retry")


def retry(
    max_attempts: int = 3,
    backoff_base: float = 2,
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
):
    """Retry a function with exponential backoff.

    Sleep pattern: backoff_base^0, backoff_base^1, ..., backoff_base^(n-2).
    With backoff_base=2 and max_attempts=4: 1s, 2s, 4s.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        log.error(f"{func.__name__} {max_attempts} denemeden sonra başarısız: {e}")
                        raise
                    wait = backoff_base ** attempt if backoff_base > 0 else 0
                    log.warning(f"{func.__name__} denemesi {attempt + 1} başarısız ({e}), {wait}s bekleniyor")
                    time.sleep(wait)
            raise last_exc  # unreachable
        return wrapper
    return decorator
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_retry.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add utils/retry.py tests/unit/test_retry.py
git commit -m "feat: add retry decorator with exponential backoff"
```

---

## Task 5: Rate Limiter Decorator

**Files:**
- Create: `utils/rate_limiter.py`
- Test: `tests/unit/test_rate_limiter.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_rate_limiter.py`:
```python
import time
from utils.rate_limiter import rate_limit


def test_rate_limit_allows_first_call_immediately():
    @rate_limit(calls_per_second=10)
    def work():
        return "ok"

    start = time.monotonic()
    work()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


def test_rate_limit_delays_second_call():
    @rate_limit(calls_per_second=10)  # min gap 0.1s
    def work():
        return "ok"

    work()
    start = time.monotonic()
    work()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


def test_rate_limit_independent_per_function():
    @rate_limit(calls_per_second=10)
    def work_a():
        return "a"

    @rate_limit(calls_per_second=10)
    def work_b():
        return "b"

    work_a()
    start = time.monotonic()
    work_b()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_rate_limiter.py -v
```
Expected: `ModuleNotFoundError: No module named 'utils.rate_limiter'`

- [ ] **Step 3: Implement `utils/rate_limiter.py`**

```python
import functools
import time
from typing import Callable


def rate_limit(calls_per_second: float):
    """Ensure at least 1/calls_per_second seconds between calls to this function.

    Each decorated function keeps its own last-call timestamp.
    """
    if calls_per_second <= 0:
        raise ValueError("calls_per_second must be positive")

    min_interval = 1.0 / calls_per_second

    def decorator(func: Callable):
        last_call = [0.0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            wait = min_interval - (now - last_call[0])
            if wait > 0:
                time.sleep(wait)
            last_call[0] = time.monotonic()
            return func(*args, **kwargs)

        return wrapper
    return decorator
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_rate_limiter.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add utils/rate_limiter.py tests/unit/test_rate_limiter.py
git commit -m "feat: add per-function rate limiter decorator"
```

---

## Task 6: Data Models

**Files:**
- Create: `storage/models.py`
- Test: `tests/unit/test_models.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_models.py`:
```python
from datetime import datetime
from dataclasses import asdict
from storage.models import ProductSnapshot


def test_product_snapshot_creates_with_all_fields():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="123456",
        name="Nemlendirici Krem",
        brand="Nivea",
        category="kozmetik",
        product_url="https://trendyol.com/p/123456",
        image_url="https://cdn.trendyol.com/p/123456.jpg",
        price=149.90,
        original_price=199.90,
        discount_rate=0.25,
        seller_name="TestMağaza",
        seller_rating=9.2,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0, 0),
    )
    assert snap.name == "Nemlendirici Krem"
    assert snap.price == 149.90
    assert snap.in_stock is True


def test_product_snapshot_optional_fields_can_be_none():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="123",
        name="Ürün",
        brand=None,
        category="kozmetik",
        product_url="https://trendyol.com/p/123",
        image_url=None,
        price=99.90,
        original_price=None,
        discount_rate=None,
        seller_name=None,
        seller_rating=None,
        in_stock=False,
        captured_at=datetime.now(),
    )
    assert snap.brand is None
    assert snap.discount_rate is None


def test_product_snapshot_to_dict():
    snap = ProductSnapshot(
        platform="trendyol",
        platform_product_id="1",
        name="x",
        brand="y",
        category="kozmetik",
        product_url="u",
        image_url="i",
        price=1.0,
        original_price=2.0,
        discount_rate=0.5,
        seller_name="s",
        seller_rating=8.0,
        in_stock=True,
        captured_at=datetime(2026, 1, 1),
    )
    d = asdict(snap)
    assert d["name"] == "x"
    assert d["price"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_models.py -v
```
Expected: `ModuleNotFoundError: No module named 'storage.models'`

- [ ] **Step 3: Implement `storage/models.py`**

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProductSnapshot:
    """Tek bir ürünün belirli bir andaki durumu.

    Scraper'lar bu tipte değer döndürür. Database katmanı bunu `products`
    ve `price_snapshots` tablolarına ayırır.
    """
    # Ürün kimliği
    platform: str
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    product_url: str
    image_url: str | None
    # Anlık veri
    price: float
    original_price: float | None
    discount_rate: float | None
    seller_name: str | None
    seller_rating: float | None
    in_stock: bool
    captured_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_models.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add storage/models.py tests/unit/test_models.py
git commit -m "feat: add ProductSnapshot dataclass"
```

---

## Task 7: Database Schema + Connection

**Files:**
- Create: `storage/migrations/001_initial.sql`
- Create: `storage/database.py` (initial version: connection + migration)
- Test: `tests/integration/test_database_schema.py`

- [ ] **Step 1: Write failing test**

`tests/integration/test_database_schema.py`:
```python
import sqlite3
from storage.database import connect, init_schema


def test_init_schema_creates_products_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='products'"
    ).fetchall()
    assert len(rows) == 1


def test_init_schema_creates_price_snapshots_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='price_snapshots'"
    ).fetchall()
    assert len(rows) == 1


def test_init_schema_creates_run_stats_table():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='run_stats'"
    ).fetchall()
    assert len(rows) == 1


def test_products_has_unique_constraint():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    conn.execute(
        "INSERT INTO products (platform, platform_product_id, name, category, product_url, "
        "first_seen_at, last_seen_at) VALUES ('trendyol', 'p1', 'a', 'kozmetik', 'u', '2026-01-01', '2026-01-01')"
    )
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO products (platform, platform_product_id, name, category, product_url, "
            "first_seen_at, last_seen_at) VALUES ('trendyol', 'p1', 'b', 'kozmetik', 'u2', '2026-01-01', '2026-01-01')"
        )


def test_init_schema_idempotent():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    init_schema(conn)  # should not raise
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    # products, price_snapshots, run_stats + sqlite internal tables
    table_names = [r[0] for r in rows if not r[0].startswith("sqlite_")]
    assert set(table_names) == {"products", "price_snapshots", "run_stats"}


def test_connect_returns_connection(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))
    assert conn is not None
    conn.execute("SELECT 1").fetchone()
    conn.close()
    assert db_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_database_schema.py -v
```
Expected: `ModuleNotFoundError: No module named 'storage.database'`

- [ ] **Step 3: Create `storage/migrations/001_initial.sql`**

```sql
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    platform_product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    product_url TEXT NOT NULL,
    image_url TEXT,
    first_seen_at TIMESTAMP NOT NULL,
    last_seen_at TIMESTAMP NOT NULL,
    UNIQUE(platform, platform_product_id)
);

CREATE INDEX IF NOT EXISTS idx_products_platform_category
    ON products(platform, category);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    price REAL NOT NULL,
    original_price REAL,
    discount_rate REAL,
    seller_name TEXT,
    seller_rating REAL,
    in_stock INTEGER NOT NULL DEFAULT 1,
    captured_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_snapshots_product_time
    ON price_snapshots(product_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS run_stats (
    run_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    category TEXT NOT NULL,
    products_found INTEGER,
    products_saved INTEGER,
    products_failed INTEGER,
    duration_seconds INTEGER,
    status TEXT NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP
);
```

- [ ] **Step 4: Implement `storage/database.py` (initial version)**

```python
import sqlite3
from pathlib import Path


_MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def connect(db_path: str) -> sqlite3.Connection:
    """SQLite bağlantısı açar, gerekirse veritabanı dosyasını oluşturur."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Tüm migration SQL dosyalarını sırayla çalıştırır. Idempotent."""
    for sql_file in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        sql = sql_file.read_text(encoding="utf-8")
        conn.executescript(sql)
    conn.commit()
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/integration/test_database_schema.py -v
```
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add storage/migrations/ storage/database.py tests/integration/test_database_schema.py
git commit -m "feat: add database schema and migration runner"
```

---

## Task 8: Database — Save Snapshots

**Files:**
- Modify: `storage/database.py` (add save_snapshot, get_latest_snapshot, get_product)
- Test: `tests/integration/test_database_operations.py`

- [ ] **Step 1: Write failing test**

`tests/integration/test_database_operations.py`:
```python
import sqlite3
from datetime import datetime
import pytest
from storage.database import (
    connect,
    init_schema,
    save_snapshot,
    get_product_by_platform_id,
    get_latest_snapshot,
)
from storage.models import ProductSnapshot


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    yield conn
    conn.close()


def _snap(**overrides) -> ProductSnapshot:
    base = dict(
        platform="trendyol",
        platform_product_id="123",
        name="Nemlendirici",
        brand="Nivea",
        category="kozmetik",
        product_url="https://trendyol.com/p/123",
        image_url="https://cdn/img.jpg",
        price=99.90,
        original_price=149.90,
        discount_rate=0.33,
        seller_name="Mağaza",
        seller_rating=9.0,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0),
    )
    base.update(overrides)
    return ProductSnapshot(**base)


def test_save_snapshot_creates_new_product(db):
    save_snapshot(db, _snap())
    row = db.execute("SELECT COUNT(*) FROM products").fetchone()
    assert row[0] == 1


def test_save_snapshot_creates_price_row(db):
    save_snapshot(db, _snap())
    row = db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()
    assert row[0] == 1


def test_save_snapshot_twice_keeps_one_product_row(db):
    save_snapshot(db, _snap(price=99.90, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(price=89.90, captured_at=datetime(2026, 4, 15)))
    products = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    snaps = db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert products == 1
    assert snaps == 2


def test_save_snapshot_updates_last_seen_at(db):
    save_snapshot(db, _snap(captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(captured_at=datetime(2026, 4, 20)))
    row = db.execute("SELECT first_seen_at, last_seen_at FROM products").fetchone()
    assert row["first_seen_at"] == "2026-04-14 00:00:00"
    assert row["last_seen_at"] == "2026-04-20 00:00:00"


def test_get_product_by_platform_id_found(db):
    save_snapshot(db, _snap())
    p = get_product_by_platform_id(db, "trendyol", "123")
    assert p is not None
    assert p["name"] == "Nemlendirici"


def test_get_product_by_platform_id_not_found(db):
    assert get_product_by_platform_id(db, "trendyol", "999") is None


def test_get_latest_snapshot_returns_most_recent(db):
    save_snapshot(db, _snap(price=100.0, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap(price=90.0, captured_at=datetime(2026, 4, 15)))
    save_snapshot(db, _snap(price=95.0, captured_at=datetime(2026, 4, 16)))

    product = get_product_by_platform_id(db, "trendyol", "123")
    latest = get_latest_snapshot(db, product["id"])
    assert latest["price"] == 95.0


def test_save_snapshot_handles_null_fields(db):
    save_snapshot(db, _snap(brand=None, original_price=None, discount_rate=None,
                             seller_name=None, seller_rating=None, image_url=None))
    row = db.execute("SELECT brand, image_url FROM products").fetchone()
    assert row["brand"] is None
    assert row["image_url"] is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_database_operations.py -v
```
Expected: `ImportError: cannot import name 'save_snapshot' from 'storage.database'`

- [ ] **Step 3: Add save_snapshot and query functions to `storage/database.py`**

Append to `storage/database.py`:
```python
from storage.models import ProductSnapshot


def save_snapshot(conn: sqlite3.Connection, snap: ProductSnapshot) -> int:
    """Ürünü upsert eder, price_snapshots'a yeni satır atar. Snapshot ID'si döner."""
    existing = get_product_by_platform_id(conn, snap.platform, snap.platform_product_id)

    if existing is None:
        cursor = conn.execute(
            """
            INSERT INTO products (
                platform, platform_product_id, name, brand, category,
                product_url, image_url, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snap.platform, snap.platform_product_id, snap.name, snap.brand,
                snap.category, snap.product_url, snap.image_url,
                snap.captured_at, snap.captured_at,
            ),
        )
        product_id = cursor.lastrowid
    else:
        product_id = existing["id"]
        conn.execute(
            """
            UPDATE products
            SET name = ?, brand = ?, product_url = ?, image_url = ?, last_seen_at = ?
            WHERE id = ?
            """,
            (snap.name, snap.brand, snap.product_url, snap.image_url, snap.captured_at, product_id),
        )

    cursor = conn.execute(
        """
        INSERT INTO price_snapshots (
            product_id, price, original_price, discount_rate,
            seller_name, seller_rating, in_stock, captured_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            product_id, snap.price, snap.original_price, snap.discount_rate,
            snap.seller_name, snap.seller_rating,
            1 if snap.in_stock else 0, snap.captured_at,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_product_by_platform_id(
    conn: sqlite3.Connection, platform: str, platform_product_id: str
) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM products WHERE platform = ? AND platform_product_id = ?",
        (platform, platform_product_id),
    ).fetchone()


def get_latest_snapshot(conn: sqlite3.Connection, product_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM price_snapshots WHERE product_id = ? ORDER BY captured_at DESC LIMIT 1",
        (product_id,),
    ).fetchone()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_database_operations.py -v
```
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add storage/database.py tests/integration/test_database_operations.py
git commit -m "feat: add save_snapshot and query operations"
```

---

## Task 9: Database — Run Stats

**Files:**
- Modify: `storage/database.py` (add start_run, finish_run)
- Test: `tests/integration/test_run_stats.py`

- [ ] **Step 1: Write failing test**

`tests/integration/test_run_stats.py`:
```python
import sqlite3
from datetime import datetime
import pytest
from storage.database import init_schema, start_run, finish_run


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    yield conn
    conn.close()


def test_start_run_inserts_row_with_running_status(db):
    start_run(db, run_id="r1", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    row = db.execute("SELECT * FROM run_stats WHERE run_id = 'r1'").fetchone()
    assert row is not None
    assert row["status"] == "running"
    assert row["platform"] == "trendyol"


def test_finish_run_updates_status_and_counts(db):
    start_run(db, run_id="r2", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    finish_run(
        db, run_id="r2",
        status="success",
        products_found=500, products_saved=498, products_failed=2,
        finished_at=datetime(2026, 4, 14, 3, 25),
        duration_seconds=1500,
        error_message=None,
    )
    row = db.execute("SELECT * FROM run_stats WHERE run_id = 'r2'").fetchone()
    assert row["status"] == "success"
    assert row["products_found"] == 500
    assert row["products_saved"] == 498
    assert row["products_failed"] == 2
    assert row["duration_seconds"] == 1500


def test_finish_run_records_error_message(db):
    start_run(db, run_id="r3", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    finish_run(
        db, run_id="r3",
        status="failed",
        products_found=0, products_saved=0, products_failed=0,
        finished_at=datetime(2026, 4, 14, 3, 1),
        duration_seconds=60,
        error_message="Anti-bot tetiklendi",
    )
    row = db.execute("SELECT error_message FROM run_stats WHERE run_id = 'r3'").fetchone()
    assert row["error_message"] == "Anti-bot tetiklendi"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_run_stats.py -v
```
Expected: `ImportError: cannot import name 'start_run' from 'storage.database'`

- [ ] **Step 3: Append to `storage/database.py`**

```python
def start_run(
    conn: sqlite3.Connection,
    run_id: str,
    platform: str,
    category: str,
    started_at: datetime,
) -> None:
    conn.execute(
        "INSERT INTO run_stats (run_id, platform, category, status, started_at) "
        "VALUES (?, ?, ?, 'running', ?)",
        (run_id, platform, category, started_at),
    )
    conn.commit()


def finish_run(
    conn: sqlite3.Connection,
    run_id: str,
    status: str,
    products_found: int,
    products_saved: int,
    products_failed: int,
    finished_at: datetime,
    duration_seconds: int,
    error_message: str | None,
) -> None:
    conn.execute(
        """
        UPDATE run_stats
        SET status = ?, products_found = ?, products_saved = ?,
            products_failed = ?, finished_at = ?, duration_seconds = ?,
            error_message = ?
        WHERE run_id = ?
        """,
        (status, products_found, products_saved, products_failed,
         finished_at, duration_seconds, error_message, run_id),
    )
    conn.commit()
```

Add `from datetime import datetime` import at top if not present.

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_run_stats.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add storage/database.py tests/integration/test_run_stats.py
git commit -m "feat: add run_stats tracking (start_run, finish_run)"
```

---

## Task 10: BaseScraper Abstract Class

**Files:**
- Create: `scrapers/base.py`
- Test: `tests/unit/test_base_scraper.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_base_scraper.py`:
```python
import pytest
from datetime import datetime
from scrapers.base import BaseScraper
from storage.models import ProductSnapshot


def test_base_scraper_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseScraper()


def test_concrete_subclass_can_be_instantiated():
    class DummyScraper(BaseScraper):
        def fetch_category(self, category_url, max_products=500):
            return []

        def close(self):
            pass

    scraper = DummyScraper()
    assert scraper.fetch_category("https://example.com") == []


def test_subclass_missing_fetch_category_fails():
    class BadScraper(BaseScraper):
        def close(self):
            pass

    with pytest.raises(TypeError):
        BadScraper()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_base_scraper.py -v
```
Expected: `ModuleNotFoundError: No module named 'scrapers.base'`

- [ ] **Step 3: Implement `scrapers/base.py`**

```python
from abc import ABC, abstractmethod
from storage.models import ProductSnapshot


class BaseScraper(ABC):
    """Tüm platform scraper'larının uyması gereken arayüz."""

    @abstractmethod
    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        """Kategori sayfasından en fazla max_products adet ürünü çeker."""

    @abstractmethod
    def close(self) -> None:
        """Kaynakları serbest bırakır (browser, bağlantı vb.)."""
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_base_scraper.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add scrapers/base.py tests/unit/test_base_scraper.py
git commit -m "feat: add BaseScraper abstract interface"
```

---

## Task 11: Trendyol Pure Parser Functions

**Files:**
- Create: `scrapers/trendyol.py` (initial version: only parse functions)
- Test: `tests/unit/test_trendyol_parsers.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_trendyol_parsers.py`:
```python
import pytest
from scrapers.trendyol import parse_price_text, parse_discount_rate


def test_parse_price_simple():
    assert parse_price_text("299,90 TL") == 299.90


def test_parse_price_with_thousands_separator():
    assert parse_price_text("1.299,90 TL") == 1299.90


def test_parse_price_without_currency():
    assert parse_price_text("149,50") == 149.50


def test_parse_price_with_extra_whitespace():
    assert parse_price_text("  299,90 TL  ") == 299.90


def test_parse_price_integer_only():
    assert parse_price_text("100 TL") == 100.0


def test_parse_price_invalid_returns_none():
    assert parse_price_text("") is None
    assert parse_price_text("fiyat yok") is None
    assert parse_price_text(None) is None


def test_parse_discount_rate_calculates_correctly():
    assert parse_discount_rate(original=200.0, current=150.0) == pytest.approx(0.25)


def test_parse_discount_rate_no_discount():
    assert parse_discount_rate(original=100.0, current=100.0) == 0.0


def test_parse_discount_rate_returns_none_when_no_original():
    assert parse_discount_rate(original=None, current=100.0) is None


def test_parse_discount_rate_returns_none_when_invalid():
    assert parse_discount_rate(original=0.0, current=100.0) is None
    assert parse_discount_rate(original=100.0, current=150.0) is None  # current > original
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/unit/test_trendyol_parsers.py -v
```
Expected: `ModuleNotFoundError: No module named 'scrapers.trendyol'`

- [ ] **Step 3: Implement parsers in `scrapers/trendyol.py`**

```python
import re


_PRICE_PATTERN = re.compile(r"[\d.,]+")


def parse_price_text(text: str | None) -> float | None:
    """Türkçe formatlı fiyat metnini float'a çevirir.

    Örnekler:
        '299,90 TL'   -> 299.90
        '1.299,90 TL' -> 1299.90
        '100 TL'      -> 100.0
    """
    if not text:
        return None
    match = _PRICE_PATTERN.search(text.strip())
    if not match:
        return None
    raw = match.group()
    # Türkçe: '.' binlik ayırıcı, ',' ondalık
    normalized = raw.replace(".", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def parse_discount_rate(original: float | None, current: float) -> float | None:
    """İndirim oranını 0-1 arası float olarak döndürür.

    original < current veya original geçersizse None döner.
    """
    if original is None or original <= 0:
        return None
    if current > original:
        return None
    return round((original - current) / original, 4)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/unit/test_trendyol_parsers.py -v
```
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add scrapers/trendyol.py tests/unit/test_trendyol_parsers.py
git commit -m "feat: add Trendyol price and discount parsers"
```

---

## Task 12: Trendyol Product Card Parser (Fixture-Based)

**Files:**
- Modify: `scrapers/trendyol.py` (add parse_product_card function)
- Create: `tests/fixtures/trendyol_product_card.html`
- Create: `tests/fixtures/trendyol_edge_cases/no_discount.html`
- Create: `tests/fixtures/trendyol_edge_cases/out_of_stock.html`
- Test: `tests/integration/test_trendyol_card_parser.py`

**IMPORTANT:** Before writing this task, the engineer must manually inspect a real Trendyol kozmetik category page in a browser (DevTools) and identify current CSS selectors for: product card container, name, price, original price, brand, seller, image, product link, out-of-stock indicator. Save a representative card as fixture HTML.

Since selectors change over time, the fixtures below use **synthetic HTML that mirrors Trendyol's structure**. Update selectors in `parse_product_card` when the engineer discovers real ones.

- [ ] **Step 1: Create fixture HTML files**

`tests/fixtures/trendyol_product_card.html`:
```html
<div class="p-card-wrppr" data-id="123456789">
  <a class="p-card-chldrn-cntnr" href="/nivea/nemlendirici-krem-p-123456789">
    <div class="p-card-img-wr">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty123/product/media/images/20240101/10/12345678/123456789/1/1_org.jpg" alt="Nivea Nemlendirici Krem" />
    </div>
    <div class="prdct-desc-cntnr-wrppr">
      <span class="prdct-desc-cntnr-ttl">Nivea</span>
      <span class="prdct-desc-cntnr-name">Nemlendirici Krem 200ml</span>
      <div class="price-item-container">
        <div class="prc-box-dscntd">149,90 TL</div>
        <div class="prc-box-orgnl">199,90 TL</div>
      </div>
      <div class="merchant-info">
        <span class="merchant-name">NiveaResmiMağaza</span>
        <span class="merchant-rating">9.2</span>
      </div>
    </div>
  </a>
</div>
```

`tests/fixtures/trendyol_edge_cases/no_discount.html`:
```html
<div class="p-card-wrppr" data-id="987654321">
  <a class="p-card-chldrn-cntnr" href="/loreal/ruj-p-987654321">
    <div class="p-card-img-wr">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty/img.jpg" alt="Loreal Ruj" />
    </div>
    <div class="prdct-desc-cntnr-wrppr">
      <span class="prdct-desc-cntnr-ttl">L'Oreal Paris</span>
      <span class="prdct-desc-cntnr-name">Color Riche Ruj</span>
      <div class="price-item-container">
        <div class="prc-box-dscntd">89,50 TL</div>
      </div>
      <div class="merchant-info">
        <span class="merchant-name">LOrealMağaza</span>
      </div>
    </div>
  </a>
</div>
```

`tests/fixtures/trendyol_edge_cases/out_of_stock.html`:
```html
<div class="p-card-wrppr" data-id="555555555">
  <a class="p-card-chldrn-cntnr" href="/marka/urun-p-555555555">
    <div class="p-card-img-wr">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty/img.jpg" alt="Ürün" />
      <div class="stmp-cntnr">
        <span class="stmp">Tükendi</span>
      </div>
    </div>
    <div class="prdct-desc-cntnr-wrppr">
      <span class="prdct-desc-cntnr-ttl">Marka</span>
      <span class="prdct-desc-cntnr-name">Ürün Adı</span>
      <div class="price-item-container">
        <div class="prc-box-dscntd">199,00 TL</div>
      </div>
    </div>
  </a>
</div>
```

- [ ] **Step 2: Write failing test**

`tests/integration/test_trendyol_card_parser.py`:
```python
from datetime import datetime
from pathlib import Path
from scrapers.trendyol import parse_product_card


FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(relative: str) -> str:
    return (FIXTURES / relative).read_text(encoding="utf-8")


def test_parse_full_card():
    html = _load("trendyol_product_card.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.platform == "trendyol"
    assert snap.platform_product_id == "123456789"
    assert snap.name == "Nemlendirici Krem 200ml"
    assert snap.brand == "Nivea"
    assert snap.price == 149.90
    assert snap.original_price == 199.90
    assert abs(snap.discount_rate - 0.25) < 0.01
    assert snap.seller_name == "NiveaResmiMağaza"
    assert snap.seller_rating == 9.2
    assert snap.image_url.startswith("https://cdn.dsmcdn.com/")
    assert snap.product_url.startswith("https://www.trendyol.com/")
    assert snap.in_stock is True


def test_parse_card_without_discount():
    html = _load("trendyol_edge_cases/no_discount.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.price == 89.50
    assert snap.original_price is None
    assert snap.discount_rate is None


def test_parse_out_of_stock_card():
    html = _load("trendyol_edge_cases/out_of_stock.html")
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert snap is not None
    assert snap.in_stock is False


def test_parse_card_without_data_id_returns_none():
    html = '<div class="p-card-wrppr"></div>'
    snap = parse_product_card(html, category="kozmetik", captured_at=datetime.now())
    assert snap is None
```

- [ ] **Step 3: Run test to verify it fails**

```bash
pytest tests/integration/test_trendyol_card_parser.py -v
```
Expected: `ImportError: cannot import name 'parse_product_card'`

- [ ] **Step 4: Implement parser**

(BeautifulSoup ve lxml Task 1'de zaten kuruldu.)

Append to `scrapers/trendyol.py`:
```python
from datetime import datetime
from bs4 import BeautifulSoup
from storage.models import ProductSnapshot


_BASE_URL = "https://www.trendyol.com"


def parse_product_card(
    html: str,
    category: str,
    captured_at: datetime,
) -> ProductSnapshot | None:
    """Tek bir ürün kartı HTML'ini ProductSnapshot'a çevirir.

    Selector şeması Trendyol'a özel. Site değişirse burası güncellenmeli.
    Parse edilemeyen kartlar için None döner (üst katmana atlama sinyali).
    """
    soup = BeautifulSoup(html, "lxml")
    wrapper = soup.select_one(".p-card-wrppr")
    if wrapper is None:
        return None

    product_id = wrapper.get("data-id")
    if not product_id:
        return None

    name_el = wrapper.select_one(".prdct-desc-cntnr-name")
    brand_el = wrapper.select_one(".prdct-desc-cntnr-ttl")
    link_el = wrapper.select_one("a.p-card-chldrn-cntnr")
    img_el = wrapper.select_one("img.p-card-img")

    price_el = wrapper.select_one(".prc-box-dscntd")
    original_price_el = wrapper.select_one(".prc-box-orgnl")

    seller_name_el = wrapper.select_one(".merchant-name")
    seller_rating_el = wrapper.select_one(".merchant-rating")

    out_of_stock_el = wrapper.select_one(".stmp")
    in_stock = True
    if out_of_stock_el and "tükendi" in out_of_stock_el.get_text(strip=True).lower():
        in_stock = False

    if name_el is None or price_el is None:
        return None

    price = parse_price_text(price_el.get_text())
    if price is None:
        return None

    original_price = parse_price_text(original_price_el.get_text()) if original_price_el else None
    discount_rate = parse_discount_rate(original_price, price)

    rating = None
    if seller_rating_el:
        try:
            rating = float(seller_rating_el.get_text(strip=True).replace(",", "."))
        except ValueError:
            rating = None

    href = link_el.get("href", "") if link_el else ""
    product_url = href if href.startswith("http") else f"{_BASE_URL}{href}"

    return ProductSnapshot(
        platform="trendyol",
        platform_product_id=product_id,
        name=name_el.get_text(strip=True),
        brand=brand_el.get_text(strip=True) if brand_el else None,
        category=category,
        product_url=product_url,
        image_url=img_el.get("src") if img_el else None,
        price=price,
        original_price=original_price,
        discount_rate=discount_rate,
        seller_name=seller_name_el.get_text(strip=True) if seller_name_el else None,
        seller_rating=rating,
        in_stock=in_stock,
        captured_at=captured_at,
    )
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/integration/test_trendyol_card_parser.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add scrapers/trendyol.py tests/fixtures/ tests/integration/test_trendyol_card_parser.py
git commit -m "feat: add Trendyol product card parser with fixture tests"
```

---

## Task 13: Trendyol Scraper — Playwright Integration

**Files:**
- Modify: `scrapers/trendyol.py` (add TrendyolScraper class)
- Test: `tests/integration/test_trendyol_scraper_offline.py`

- [ ] **Step 1: Write failing test (using full category fixture page)**

First create `tests/fixtures/trendyol_category_page.html` by wrapping 3 cards:
```html
<!DOCTYPE html>
<html lang="tr">
<head><meta charset="utf-8"><title>Kozmetik</title></head>
<body>
<div class="prdct-cntnr-wrppr">
  <div class="p-card-wrppr" data-id="111">
    <a class="p-card-chldrn-cntnr" href="/urun-1-p-111">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty/u1.jpg" alt="Ürün 1" />
      <span class="prdct-desc-cntnr-ttl">Marka1</span>
      <span class="prdct-desc-cntnr-name">Ürün 1</span>
      <div class="prc-box-dscntd">99,90 TL</div>
      <div class="prc-box-orgnl">149,90 TL</div>
      <span class="merchant-name">Satıcı1</span>
      <span class="merchant-rating">9.0</span>
    </a>
  </div>
  <div class="p-card-wrppr" data-id="222">
    <a class="p-card-chldrn-cntnr" href="/urun-2-p-222">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty/u2.jpg" alt="Ürün 2" />
      <span class="prdct-desc-cntnr-ttl">Marka2</span>
      <span class="prdct-desc-cntnr-name">Ürün 2</span>
      <div class="prc-box-dscntd">199,00 TL</div>
      <span class="merchant-name">Satıcı2</span>
    </a>
  </div>
  <div class="p-card-wrppr" data-id="333">
    <a class="p-card-chldrn-cntnr" href="/urun-3-p-333">
      <img class="p-card-img" src="https://cdn.dsmcdn.com/ty/u3.jpg" alt="Ürün 3" />
      <span class="prdct-desc-cntnr-ttl">Marka3</span>
      <span class="prdct-desc-cntnr-name">Ürün 3</span>
      <div class="prc-box-dscntd">299,90 TL</div>
      <span class="merchant-name">Satıcı3</span>
    </a>
  </div>
</div>
</body>
</html>
```

`tests/integration/test_trendyol_scraper_offline.py`:
```python
from datetime import datetime
from pathlib import Path
from scrapers.trendyol import extract_cards_from_page


FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_extract_cards_returns_all_products():
    html = (FIXTURES / "trendyol_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert len(snaps) == 3
    ids = {s.platform_product_id for s in snaps}
    assert ids == {"111", "222", "333"}


def test_extract_cards_respects_max_products_limit():
    html = (FIXTURES / "trendyol_category_page.html").read_text(encoding="utf-8")
    snaps = extract_cards_from_page(
        html, category="kozmetik", captured_at=datetime(2026, 4, 14), max_products=2,
    )
    assert len(snaps) == 2


def test_extract_cards_skips_unparseable():
    html = """
    <div class="prdct-cntnr-wrppr">
      <div class="p-card-wrppr" data-id="111">
        <a class="p-card-chldrn-cntnr" href="/u-p-111">
          <span class="prdct-desc-cntnr-name">İyi Ürün</span>
          <div class="prc-box-dscntd">99,90 TL</div>
        </a>
      </div>
      <div class="p-card-wrppr"><!-- data-id eksik --></div>
      <div class="p-card-wrppr" data-id="333">
        <a class="p-card-chldrn-cntnr" href="/u-p-333">
          <span class="prdct-desc-cntnr-name">Diğer Ürün</span>
          <div class="prc-box-dscntd">149,50 TL</div>
        </a>
      </div>
    </div>
    """
    snaps = extract_cards_from_page(html, category="kozmetik", captured_at=datetime(2026, 4, 14))
    assert len(snaps) == 2
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_trendyol_scraper_offline.py -v
```
Expected: `ImportError: cannot import name 'extract_cards_from_page'`

- [ ] **Step 3: Add `extract_cards_from_page` + `TrendyolScraper` to `scrapers/trendyol.py`**

Append to `scrapers/trendyol.py`:
```python
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, Page, Browser

from config import settings
from scrapers.base import BaseScraper
from utils.logger import get_logger
from utils.retry import retry
from utils.rate_limiter import rate_limit

log = get_logger("trendyol")

_CARD_SELECTOR = ".p-card-wrppr"


def extract_cards_from_page(
    html: str,
    category: str,
    captured_at: datetime,
    max_products: int | None = None,
) -> list[ProductSnapshot]:
    """Tam kategori sayfasından ürün kartlarını parse eder.

    Parse edilemeyen kartları atlar (logla, devam et).
    """
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select(_CARD_SELECTOR)
    snapshots: list[ProductSnapshot] = []

    for card in cards:
        if max_products is not None and len(snapshots) >= max_products:
            break

        snap = parse_product_card(str(card), category=category, captured_at=captured_at)
        if snap is None:
            log.warning(f"Kart parse edilemedi (data-id={card.get('data-id')}), atlandı")
            continue
        snapshots.append(snap)

    return snapshots


class TrendyolScraper(BaseScraper):
    """Playwright ile Trendyol kategori sayfalarını çeker."""

    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None

    def _ensure_browser(self) -> Browser:
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=settings.scraper_headless,
            )
        return self._browser

    @rate_limit(calls_per_second=settings.scraper_requests_per_second)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=45000)
        self._scroll_to_load(page)
        return page.content()

    def _scroll_to_load(self, page: Page, max_scrolls: int = 10) -> None:
        """Infinite scroll sayfasında aşağı in, daha fazla ürün yüklet."""
        for _ in range(max_scrolls):
            previous_height = page.evaluate("document.body.scrollHeight")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)
            new_height = page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break

    def fetch_category(
        self,
        category_url: str,
        max_products: int = 500,
    ) -> list[ProductSnapshot]:
        browser = self._ensure_browser()
        context = browser.new_context(user_agent=settings.scraper_user_agent)
        page = context.new_page()
        try:
            html = self._load_page(page, category_url)
            captured_at = datetime.now()
            snapshots = extract_cards_from_page(
                html,
                category=self._infer_category_from_url(category_url),
                captured_at=captured_at,
                max_products=max_products,
            )
            log.info(f"{len(snapshots)} ürün çekildi")
            return snapshots
        finally:
            context.close()

    def _infer_category_from_url(self, url: str) -> str:
        """URL'den kategori adını çıkar. Örn: .../kozmetik-x-c89 -> 'kozmetik'."""
        url_lower = url.lower()
        known = ["kozmetik", "elektronik", "giyim", "ev-yasam", "kitap"]
        for k in known:
            if k in url_lower:
                return k
        return "unknown"

    def close(self) -> None:
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_trendyol_scraper_offline.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Run full test suite (non-e2e)**

```bash
pytest -v
```
Expected: all unit + integration tests pass.

- [ ] **Step 6: Commit**

```bash
git add scrapers/trendyol.py tests/fixtures/trendyol_category_page.html tests/integration/test_trendyol_scraper_offline.py
git commit -m "feat: add TrendyolScraper with Playwright and card extraction"
```

---

## Task 14: Trendyol E2E Test (Real Site)

**Files:**
- Create: `tests/e2e/test_trendyol_live.py`

- [ ] **Step 1: Identify real Trendyol cosmetics URL**

Open Trendyol in a browser, navigate to the cosmetics category, copy the URL. Commonly `https://www.trendyol.com/kozmetik-x-c89` (verify current URL before running test).

- [ ] **Step 2: Write E2E test**

`tests/e2e/test_trendyol_live.py`:
```python
import pytest
from scrapers.trendyol import TrendyolScraper


TRENDYOL_KOZMETIK_URL = "https://www.trendyol.com/kozmetik-x-c89"


@pytest.mark.e2e
def test_trendyol_scraper_fetches_real_products():
    """Gerçek Trendyol'a bağlanır, 5 ürün çeker.

    Selector değişikliklerini erken tespit etmek için haftada 1 çalıştır.
    """
    scraper = TrendyolScraper()
    try:
        snapshots = scraper.fetch_category(TRENDYOL_KOZMETIK_URL, max_products=5)
    finally:
        scraper.close()

    assert len(snapshots) >= 3, f"En az 3 ürün beklendi, {len(snapshots)} bulundu"

    for snap in snapshots:
        assert snap.platform == "trendyol"
        assert snap.platform_product_id
        assert snap.name
        assert snap.price > 0
        assert snap.product_url.startswith("https://www.trendyol.com/")
```

- [ ] **Step 3: Run E2E test manually**

```bash
pytest -m e2e tests/e2e/test_trendyol_live.py -v -s
```

Expected: PASS (takes 30-60 seconds — browser opens, page loads, products extract).

**If it fails:** The most likely cause is selector drift. Open the real page in browser DevTools, inspect the current card class names, and update selectors in `scrapers/trendyol.py` (`_CARD_SELECTOR`, `parse_product_card` selectors). Then update fixture HTML files to match and re-run the relevant integration tests.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_trendyol_live.py
git commit -m "test: add Trendyol E2E live scraper test"
```

---

## Task 15: Main Pipeline

**Files:**
- Create: `main.py`
- Test: `tests/integration/test_main_pipeline.py`

- [ ] **Step 1: Write failing test (with mocked scraper)**

`tests/integration/test_main_pipeline.py`:
```python
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock
import pytest

from main import run_pipeline
from storage.database import init_schema
from storage.models import ProductSnapshot


@pytest.fixture
def in_memory_db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)

    def fake_connect(_path):
        return conn

    monkeypatch.setattr("main.connect", fake_connect)
    yield conn
    conn.close()


def _fake_snap(pid: str, price: float) -> ProductSnapshot:
    return ProductSnapshot(
        platform="trendyol",
        platform_product_id=pid,
        name=f"Ürün {pid}",
        brand="Marka",
        category="kozmetik",
        product_url=f"https://trendyol.com/p/{pid}",
        image_url=None,
        price=price,
        original_price=None,
        discount_rate=None,
        seller_name="Satıcı",
        seller_rating=None,
        in_stock=True,
        captured_at=datetime(2026, 4, 14, 3, 0),
    )


def test_run_pipeline_saves_all_snapshots(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.return_value = [
        _fake_snap("1", 100.0),
        _fake_snap("2", 200.0),
        _fake_snap("3", 300.0),
    ]

    stats = run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    assert stats["status"] == "success"
    assert stats["products_saved"] == 3
    assert stats["products_failed"] == 0

    count = in_memory_db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0]
    assert count == 3


def test_run_pipeline_records_run_stats(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.return_value = [_fake_snap("1", 100.0)]

    run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    row = in_memory_db.execute("SELECT * FROM run_stats").fetchone()
    assert row is not None
    assert row["status"] == "success"
    assert row["products_found"] == 1


def test_run_pipeline_handles_scraper_exception(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.side_effect = RuntimeError("Anti-bot tetiklendi")

    stats = run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    assert stats["status"] == "failed"
    assert "Anti-bot" in stats["error_message"]

    row = in_memory_db.execute("SELECT status, error_message FROM run_stats").fetchone()
    assert row["status"] == "failed"
    assert "Anti-bot" in row["error_message"]


def test_run_pipeline_closes_scraper_even_on_error(in_memory_db):
    fake_scraper = MagicMock()
    fake_scraper.fetch_category.side_effect = RuntimeError("boom")

    run_pipeline(
        scraper=fake_scraper,
        category_url="https://trendyol.com/kozmetik",
        category_name="kozmetik",
        max_products=500,
    )

    fake_scraper.close.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/integration/test_main_pipeline.py -v
```
Expected: `ModuleNotFoundError: No module named 'main'` or `ImportError: cannot import name 'run_pipeline'`

- [ ] **Step 3: Implement `main.py`**

```python
"""Metrio — Günlük scraping pipeline'ı."""

import sys
import time
import traceback
import uuid
from datetime import datetime

from config import settings
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
        conn.close()

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


def main() -> int:
    """CLI giriş noktası. Default kategori listesini çalıştırır."""
    overall_status = 0
    for cat in _DEFAULT_CATEGORIES:
        scraper = TrendyolScraper()
        stats = run_pipeline(
            scraper=scraper,
            category_url=cat["url"],
            category_name=cat["name"],
            max_products=settings.scraper_max_products,
        )
        if stats["status"] == "failed":
            overall_status = 1
    return overall_status


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/integration/test_main_pipeline.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Run all non-e2e tests**

```bash
pytest -v
```
Expected: all unit + integration tests pass (~30+ tests).

- [ ] **Step 6: Commit**

```bash
git add main.py tests/integration/test_main_pipeline.py
git commit -m "feat: add main pipeline orchestration"
```

---

## Task 16: End-to-End Manual Run + Scheduler Setup

**Files:**
- Modify: `README.md` (add scheduler instructions + manual run log)

- [ ] **Step 1: Run the full pipeline manually against real Trendyol**

```bash
source .venv/Scripts/activate
python main.py
```

Expected:
- Console shows INFO log lines: "Çekim başladı", "N ürün tespit edildi", "N kaydedildi"
- `data/metrio.db` is created
- `logs/scraper.log` contains the run log
- Exit code 0

- [ ] **Step 2: Verify data was saved correctly**

```bash
python -c "import sqlite3; c=sqlite3.connect('data/metrio.db'); print('products:', c.execute('SELECT COUNT(*) FROM products').fetchone()[0]); print('snapshots:', c.execute('SELECT COUNT(*) FROM price_snapshots').fetchone()[0]); print('runs:', c.execute('SELECT status, products_saved FROM run_stats').fetchall())"
```

Expected: `products: >=50`, `snapshots: >=50`, `runs: [('success', >=50)]`

- [ ] **Step 3: Update `README.md` with Windows Task Scheduler instructions**

Append to `README.md`:
```markdown
## Günlük Otomatik Çalıştırma (Windows)

1. `run_daily.bat` dosyası oluştur:
   ```bat
   @echo off
   cd /d "c:\Users\altun\Desktop\Yeni klasör\verimadenciligi"
   call .venv\Scripts\activate.bat
   python main.py
   ```

2. Windows Task Scheduler aç (`Win + R` → `taskschd.msc`)
3. "Create Basic Task" → İsim: "Metrio Günlük Çekim"
4. Trigger: Daily, saat 03:00
5. Action: Start a program → `run_daily.bat` dosyasını seç
6. "Run whether user is logged on or not" işaretle
7. Test et: Task'a sağ tık → Run

## Manuel Test Çalıştırması

- Tüm testler (E2E hariç): `pytest`
- Sadece E2E: `pytest -m e2e`
- Tek dosya: `pytest tests/unit/test_trendyol_parsers.py -v`
```

- [ ] **Step 4: Create `run_daily.bat`**

```bat
@echo off
cd /d "c:\Users\altun\Desktop\Yeni klasör\verimadenciligi"
call .venv\Scripts\activate.bat
python main.py
```

- [ ] **Step 5: Commit**

```bash
git add README.md run_daily.bat
git commit -m "docs: add scheduler setup and run_daily.bat for Windows"
```

- [ ] **Step 6: Verify Hafta 1 success criteria**

Run each check and confirm:
- [ ] `pytest` passes all unit + integration tests
- [ ] `pytest -m e2e` passes (real Trendyol)
- [ ] `python main.py` runs end-to-end with exit code 0
- [ ] `data/metrio.db` contains 50+ products, 50+ snapshots
- [ ] `logs/scraper.log` has structured entries
- [ ] All 7 data fields captured (check a sample row)
- [ ] Git log shows 16 focused commits
