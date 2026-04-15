# Metrio — Hafta 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4 analiz modülü (fiyat değişimi, anomali, trend, yorum) ve Streamlit dashboard inşa ederek müşteriye gösterilebilir içgörüler üretmek.

**Architecture:** Analiz modülleri saf fonksiyonlar (SQLite'a read-only). Dashboard Streamlit + Plotly, analizden çağırır. Demo için seed scripti 30 gün sentetik geçmiş üretir.

**Tech Stack:** Streamlit 1.39, Plotly 5.24, Pandas 2.2, pytest (Hafta 1'den).

---

## File Structure

**Create:**
- `analysis/queries.py`, `analysis/price_changes.py`, `analysis/anomaly.py`, `analysis/trends.py`, `analysis/product_history.py`, `analysis/commentary.py`
- `dashboard/app.py`, `dashboard/pages/2_🎯_Fırsatlar.py`, `dashboard/pages/3_🚨_Anomaliler.py`, `dashboard/pages/4_📈_Trendler.py`, `dashboard/pages/5_🔍_Ürün_Detay.py`
- `dashboard/components/charts.py`, `dashboard/components/cards.py`, `dashboard/components/filters.py`, `dashboard/components/exports.py`
- `dashboard/.streamlit/config.toml`
- `scripts/seed_demo_history.py`
- Tests: `tests/unit/test_{analysis_module}.py`, `tests/integration/test_analysis_queries.py`

---

## Task 1: Install Dependencies

- [ ] **Step 1: Update requirements.txt**

Append to `requirements.txt`:
```
streamlit==1.39.0
plotly==5.24.1
pandas==2.2.3
```

- [ ] **Step 2: Install**

```bash
source .venv/Scripts/activate
pip install streamlit==1.39.0 plotly==5.24.1 pandas==2.2.3
```

- [ ] **Step 3: Verify**

```bash
streamlit --version
python -c "import plotly, pandas; print(plotly.__version__, pandas.__version__)"
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add streamlit, plotly, pandas dependencies for Hafta 2"
```

---

## Task 2: Analysis Queries Helper

**Files:**
- Create: `analysis/__init__.py`, `analysis/queries.py`
- Test: `tests/integration/test_analysis_queries.py`

- [ ] **Step 1: Write failing test**

`tests/integration/test_analysis_queries.py`:
```python
import sqlite3
from datetime import datetime
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.queries import (
    get_latest_snapshots_df,
    get_price_history_df,
    get_unique_brands,
    get_unique_categories,
)


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, brand="Nivea", captured_at=datetime(2026, 4, 14)):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=captured_at,
    )


def test_get_latest_snapshots_df_returns_one_row_per_product(db):
    save_snapshot(db, _snap("1", 100, captured_at=datetime(2026, 4, 10)))
    save_snapshot(db, _snap("1", 90, captured_at=datetime(2026, 4, 14)))
    save_snapshot(db, _snap("2", 200, captured_at=datetime(2026, 4, 14)))

    df = get_latest_snapshots_df(db)
    assert len(df) == 2
    prices = dict(zip(df["platform_product_id"], df["price"]))
    assert prices["1"] == 90  # latest
    assert prices["2"] == 200


def test_get_price_history_df_orders_chronologically(db):
    save_snapshot(db, _snap("1", 100, captured_at=datetime(2026, 4, 10)))
    save_snapshot(db, _snap("1", 95, captured_at=datetime(2026, 4, 12)))
    save_snapshot(db, _snap("1", 90, captured_at=datetime(2026, 4, 14)))

    product_id = db.execute("SELECT id FROM products").fetchone()[0]
    df = get_price_history_df(db, product_id)
    assert len(df) == 3
    assert list(df["price"]) == [100, 95, 90]


def test_get_unique_brands_returns_sorted_list(db):
    save_snapshot(db, _snap("1", 100, brand="Nivea"))
    save_snapshot(db, _snap("2", 200, brand="Loreal"))
    save_snapshot(db, _snap("3", 150, brand="Nivea"))

    brands = get_unique_brands(db)
    assert brands == ["Loreal", "Nivea"]


def test_get_unique_categories_returns_list(db):
    save_snapshot(db, _snap("1", 100))
    cats = get_unique_categories(db)
    assert cats == ["kozmetik"]
```

- [ ] **Step 2: Run, expect fail**
```bash
pytest tests/integration/test_analysis_queries.py -v
```

- [ ] **Step 3: Implement `analysis/__init__.py` (empty)**

- [ ] **Step 4: Implement `analysis/queries.py`**

```python
import sqlite3
from datetime import datetime
import pandas as pd


def get_latest_snapshots_df(conn: sqlite3.Connection) -> pd.DataFrame:
    """Her ürün için en son snapshot'ı tek satır halinde döner."""
    query = """
        SELECT p.id AS product_id, p.platform, p.platform_product_id,
               p.name, p.brand, p.category, p.product_url, p.image_url,
               s.price, s.original_price, s.discount_rate,
               s.seller_rating, s.in_stock, s.captured_at
        FROM products p
        JOIN (
            SELECT product_id, MAX(captured_at) AS max_at
            FROM price_snapshots GROUP BY product_id
        ) latest ON latest.product_id = p.id
        JOIN price_snapshots s
            ON s.product_id = p.id AND s.captured_at = latest.max_at
    """
    return pd.read_sql_query(query, conn)


def get_price_history_df(conn: sqlite3.Connection, product_id: int) -> pd.DataFrame:
    query = """
        SELECT price, original_price, discount_rate, in_stock, captured_at
        FROM price_snapshots
        WHERE product_id = ?
        ORDER BY captured_at ASC
    """
    return pd.read_sql_query(query, conn, params=(product_id,))


def get_unique_brands(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT brand FROM products WHERE brand IS NOT NULL ORDER BY brand"
    ).fetchall()
    return [r[0] for r in rows]


def get_unique_categories(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()
    return [r[0] for r in rows]


def get_date_range(conn: sqlite3.Connection) -> tuple[datetime | None, datetime | None]:
    row = conn.execute(
        "SELECT MIN(captured_at), MAX(captured_at) FROM price_snapshots"
    ).fetchone()
    return (row[0], row[1]) if row and row[0] else (None, None)
```

- [ ] **Step 5: Run, expect pass**
```bash
pytest tests/integration/test_analysis_queries.py -v
```

- [ ] **Step 6: Commit**
```bash
git add analysis/__init__.py analysis/queries.py tests/integration/test_analysis_queries.py
git commit -m "feat: add analysis queries helper module"
```

---

## Task 3: Price Changes Module

**Files:**
- Create: `analysis/price_changes.py`
- Test: `tests/unit/test_price_changes.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_price_changes.py`:
```python
import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.price_changes import top_movers, PriceChange


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, days_ago, brand="Nivea"):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_top_movers_finds_biggest_drops(db):
    # Product 1: 100 -> 80 (-20%)
    save_snapshot(db, _snap("1", 100, days_ago=6))
    save_snapshot(db, _snap("1", 80, days_ago=0))
    # Product 2: 200 -> 150 (-25%)
    save_snapshot(db, _snap("2", 200, days_ago=6))
    save_snapshot(db, _snap("2", 150, days_ago=0))
    # Product 3: 50 -> 55 (+10%, opposite direction)
    save_snapshot(db, _snap("3", 50, days_ago=6))
    save_snapshot(db, _snap("3", 55, days_ago=0))

    movers = top_movers(db, days=7, direction="down")
    assert len(movers) == 2
    assert movers[0].platform_product_id == "2"  # biggest drop first
    assert movers[0].change_percent == pytest.approx(-0.25)


def test_top_movers_includes_both_directions(db):
    save_snapshot(db, _snap("1", 100, days_ago=6))
    save_snapshot(db, _snap("1", 80, days_ago=0))
    save_snapshot(db, _snap("2", 50, days_ago=6))
    save_snapshot(db, _snap("2", 60, days_ago=0))

    movers = top_movers(db, days=7, direction="both")
    assert len(movers) == 2


def test_top_movers_ignores_products_with_single_snapshot(db):
    save_snapshot(db, _snap("1", 100, days_ago=0))

    movers = top_movers(db, days=7)
    assert len(movers) == 0


def test_top_movers_respects_limit(db):
    for i in range(10):
        save_snapshot(db, _snap(str(i), 100, days_ago=6))
        save_snapshot(db, _snap(str(i), 80 + i, days_ago=0))

    movers = top_movers(db, days=7, limit=3)
    assert len(movers) == 3


def test_price_change_has_dataclass_fields():
    pc = PriceChange(
        product_id=1, platform_product_id="p1", name="x", brand="y",
        category="kozmetik", old_price=100, new_price=80,
        change_amount=-20, change_percent=-0.2,
        captured_at_old=datetime(2026, 4, 1), captured_at_new=datetime(2026, 4, 7),
        product_url="https://example.com",
    )
    assert pc.change_percent == -0.2
```

- [ ] **Step 2: Run, expect fail**
```bash
pytest tests/unit/test_price_changes.py -v
```

- [ ] **Step 3: Implement `analysis/price_changes.py`**

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class PriceChange:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    old_price: float
    new_price: float
    change_amount: float
    change_percent: float
    captured_at_old: datetime
    captured_at_new: datetime
    product_url: str


def top_movers(
    conn: sqlite3.Connection,
    days: int = 7,
    limit: int = 20,
    direction: Literal["down", "up", "both"] = "both",
) -> list[PriceChange]:
    """Son N günde fiyat hareketi olan ürünleri bulur."""
    cutoff = datetime.now() - timedelta(days=days)

    query = """
        WITH product_range AS (
            SELECT s.product_id,
                   MIN(s.captured_at) AS first_at,
                   MAX(s.captured_at) AS last_at
            FROM price_snapshots s
            WHERE s.captured_at >= ?
            GROUP BY s.product_id
            HAVING COUNT(*) >= 2
        )
        SELECT p.id, p.platform_product_id, p.name, p.brand, p.category,
               p.product_url,
               s_old.price AS old_price, s_old.captured_at AS old_at,
               s_new.price AS new_price, s_new.captured_at AS new_at
        FROM product_range pr
        JOIN products p ON p.id = pr.product_id
        JOIN price_snapshots s_old
            ON s_old.product_id = pr.product_id AND s_old.captured_at = pr.first_at
        JOIN price_snapshots s_new
            ON s_new.product_id = pr.product_id AND s_new.captured_at = pr.last_at
        WHERE s_old.price != s_new.price
    """
    rows = conn.execute(query, (cutoff,)).fetchall()

    changes = []
    for r in rows:
        change_amount = r["new_price"] - r["old_price"]
        if r["old_price"] == 0:
            continue
        change_percent = change_amount / r["old_price"]

        if direction == "down" and change_percent >= 0:
            continue
        if direction == "up" and change_percent <= 0:
            continue

        changes.append(PriceChange(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            category=r["category"],
            old_price=r["old_price"],
            new_price=r["new_price"],
            change_amount=change_amount,
            change_percent=change_percent,
            captured_at_old=datetime.fromisoformat(r["old_at"]),
            captured_at_new=datetime.fromisoformat(r["new_at"]),
            product_url=r["product_url"],
        ))

    # Büyük hareketten küçüğe (mutlak değer)
    changes.sort(key=lambda c: abs(c.change_percent), reverse=True)
    return changes[:limit]
```

- [ ] **Step 4: Run, expect pass**

- [ ] **Step 5: Commit**
```bash
git add analysis/price_changes.py tests/unit/test_price_changes.py
git commit -m "feat: add price_changes analysis (top movers)"
```

---

## Task 4: Anomaly Detection Module

**Files:**
- Create: `analysis/anomaly.py`
- Test: `tests/unit/test_anomaly.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_anomaly.py`:
```python
import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.anomaly import detect_anomalies, Anomaly


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, days_ago, brand="Nivea"):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_detects_price_drop_anomaly(db):
    # 30 gün boyunca 100 TL, sonra aniden 60 TL (%40 düşüş)
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 60, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 1
    assert anomalies[0].direction == "drop"
    assert anomalies[0].deviation_percent < -0.30


def test_detects_price_spike_anomaly(db):
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 140, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 1
    assert anomalies[0].direction == "spike"


def test_ignores_minor_changes(db):
    for days_ago in range(30, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 105, days_ago=0))  # %5 artış, eşik altı

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert len(anomalies) == 0


def test_low_confidence_for_sparse_data(db):
    save_snapshot(db, _snap("1", 100, days_ago=5))
    save_snapshot(db, _snap("1", 50, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    if anomalies:
        assert anomalies[0].confidence == "low"


def test_high_confidence_for_dense_data(db):
    for days_ago in range(20, 0, -1):
        save_snapshot(db, _snap("1", 100, days_ago=days_ago))
    save_snapshot(db, _snap("1", 50, days_ago=0))

    anomalies = detect_anomalies(db, threshold_percent=0.20)
    assert anomalies[0].confidence == "high"
```

- [ ] **Step 2: Run, expect fail**

- [ ] **Step 3: Implement `analysis/anomaly.py`**

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class Anomaly:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    category: str
    current_price: float
    average_price: float
    deviation_percent: float
    direction: Literal["drop", "spike"]
    confidence: Literal["low", "medium", "high"]
    snapshot_count: int
    product_url: str


def _confidence(count: int) -> str:
    if count < 5:
        return "low"
    if count < 15:
        return "medium"
    return "high"


def detect_anomalies(
    conn: sqlite3.Connection,
    lookback_days: int = 30,
    threshold_percent: float = 0.20,
) -> list[Anomaly]:
    """Son N günün ortalamasından eşiği aşan sapmaları bulur."""
    cutoff = datetime.now() - timedelta(days=lookback_days)

    query = """
        SELECT p.id, p.platform_product_id, p.name, p.brand, p.category, p.product_url,
               (SELECT price FROM price_snapshots s2
                WHERE s2.product_id = p.id ORDER BY s2.captured_at DESC LIMIT 1) AS current_price,
               AVG(s.price) AS avg_price,
               COUNT(s.id) AS snap_count
        FROM products p
        JOIN price_snapshots s ON s.product_id = p.id
        WHERE s.captured_at >= ?
        GROUP BY p.id
        HAVING snap_count >= 2
    """
    rows = conn.execute(query, (cutoff,)).fetchall()

    anomalies = []
    for r in rows:
        current = r["current_price"]
        avg = r["avg_price"]
        if avg == 0:
            continue
        deviation = (current - avg) / avg
        if abs(deviation) < threshold_percent:
            continue

        direction = "spike" if deviation > 0 else "drop"
        anomalies.append(Anomaly(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            category=r["category"],
            current_price=current,
            average_price=avg,
            deviation_percent=deviation,
            direction=direction,
            confidence=_confidence(r["snap_count"]),
            snapshot_count=r["snap_count"],
            product_url=r["product_url"],
        ))

    anomalies.sort(key=lambda a: abs(a.deviation_percent), reverse=True)
    return anomalies
```

- [ ] **Step 4: Run, expect pass**
- [ ] **Step 5: Commit**
```bash
git add analysis/anomaly.py tests/unit/test_anomaly.py
git commit -m "feat: add anomaly detection based on 30-day average deviation"
```

---

## Task 5: Trends Module

**Files:**
- Create: `analysis/trends.py`
- Test: `tests/unit/test_trends.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_trends.py`:
```python
import sqlite3
from datetime import datetime, timedelta, date
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.trends import brand_trend, category_trend


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, days_ago, brand="Nivea", category="kozmetik"):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=f"Urun {pid}",
        brand=brand, category=category,
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_brand_trend_returns_daily_averages(db):
    save_snapshot(db, _snap("1", 100, days_ago=2, brand="Nivea"))
    save_snapshot(db, _snap("2", 200, days_ago=2, brand="Nivea"))
    save_snapshot(db, _snap("1", 110, days_ago=1, brand="Nivea"))

    points = brand_trend(db, brand="Nivea", days=7)
    assert len(points) >= 2
    for p in points:
        assert p.product_count > 0
        assert p.average_price > 0


def test_brand_trend_filters_by_brand(db):
    save_snapshot(db, _snap("1", 100, days_ago=1, brand="Nivea"))
    save_snapshot(db, _snap("2", 500, days_ago=1, brand="Loreal"))

    points = brand_trend(db, brand="Nivea", days=7)
    for p in points:
        assert p.average_price == 100  # Sadece Nivea


def test_category_trend(db):
    save_snapshot(db, _snap("1", 100, days_ago=1, category="kozmetik"))
    save_snapshot(db, _snap("2", 500, days_ago=1, category="elektronik"))

    kozmetik = category_trend(db, category="kozmetik", days=7)
    for p in kozmetik:
        assert p.average_price == 100
```

- [ ] **Step 2: Implement `analysis/trends.py`**

```python
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass
class TrendPoint:
    date: date
    average_price: float
    median_price: float
    product_count: int


def _aggregate_query(
    conn: sqlite3.Connection,
    where_clause: str,
    params: tuple,
    days: int,
) -> list[TrendPoint]:
    cutoff = datetime.now() - timedelta(days=days)
    query = f"""
        SELECT DATE(s.captured_at) AS day,
               AVG(s.price) AS avg_price,
               COUNT(DISTINCT s.product_id) AS product_count,
               GROUP_CONCAT(s.price) AS price_list
        FROM price_snapshots s
        JOIN products p ON p.id = s.product_id
        WHERE s.captured_at >= ? AND {where_clause}
        GROUP BY day
        ORDER BY day ASC
    """
    rows = conn.execute(query, (cutoff, *params)).fetchall()

    points = []
    for r in rows:
        prices = sorted(float(x) for x in r["price_list"].split(","))
        n = len(prices)
        median = prices[n // 2] if n % 2 else (prices[n // 2 - 1] + prices[n // 2]) / 2
        points.append(TrendPoint(
            date=date.fromisoformat(r["day"]),
            average_price=r["avg_price"],
            median_price=median,
            product_count=r["product_count"],
        ))
    return points


def brand_trend(conn, brand: str, days: int = 30) -> list[TrendPoint]:
    return _aggregate_query(conn, "p.brand = ?", (brand,), days)


def category_trend(conn, category: str, days: int = 30) -> list[TrendPoint]:
    return _aggregate_query(conn, "p.category = ?", (category,), days)
```

- [ ] **Step 3: Run tests, expect pass**
- [ ] **Step 4: Commit**
```bash
git add analysis/trends.py tests/unit/test_trends.py
git commit -m "feat: add brand/category trend analysis"
```

---

## Task 6: Product History Module

**Files:**
- Create: `analysis/product_history.py`
- Test: `tests/unit/test_product_history.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_product_history.py`:
```python
import sqlite3
from datetime import datetime, timedelta
import pytest
from storage.database import init_schema, save_snapshot
from storage.models import ProductSnapshot
from analysis.product_history import search_products, get_product_history


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    return conn


def _snap(pid, price, name="Nivea Krem", days_ago=0):
    return ProductSnapshot(
        platform="trendyol", platform_product_id=pid, name=name,
        brand="Nivea", category="kozmetik",
        product_url=f"https://trendyol.com/{pid}", image_url=None,
        price=price, original_price=None, discount_rate=None,
        seller_name=None, seller_rating=None, in_stock=True,
        captured_at=datetime.now() - timedelta(days=days_ago),
    )


def test_search_finds_by_name_substring(db):
    save_snapshot(db, _snap("1", 100, name="Nivea Nemlendirici Krem"))
    save_snapshot(db, _snap("2", 200, name="Loreal Ruj"))

    results = search_products(db, "nemlendirici")
    assert len(results) == 1
    assert results[0].platform_product_id == "1"


def test_search_case_insensitive(db):
    save_snapshot(db, _snap("1", 100, name="Nivea Nemlendirici"))
    results = search_products(db, "NEMLENDIRICI")
    assert len(results) == 1


def test_get_product_history_returns_ordered(db):
    save_snapshot(db, _snap("1", 100, days_ago=2))
    save_snapshot(db, _snap("1", 90, days_ago=1))
    save_snapshot(db, _snap("1", 85, days_ago=0))

    product_id = db.execute("SELECT id FROM products").fetchone()[0]
    history = get_product_history(db, product_id)
    assert len(history) == 3
    assert history[0].price > history[-1].price
```

- [ ] **Step 2: Implement `analysis/product_history.py`**

```python
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ProductMatch:
    product_id: int
    platform_product_id: str
    name: str
    brand: str | None
    current_price: float


@dataclass
class HistoryPoint:
    captured_at: datetime
    price: float
    original_price: float | None
    discount_rate: float | None
    in_stock: bool


def search_products(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[ProductMatch]:
    pattern = f"%{query.lower()}%"
    rows = conn.execute("""
        SELECT p.id, p.platform_product_id, p.name, p.brand,
               (SELECT price FROM price_snapshots
                WHERE product_id = p.id ORDER BY captured_at DESC LIMIT 1) AS cur_price
        FROM products p
        WHERE LOWER(p.name) LIKE ? OR LOWER(p.brand) LIKE ?
        ORDER BY p.name ASC
        LIMIT ?
    """, (pattern, pattern, limit)).fetchall()

    return [
        ProductMatch(
            product_id=r["id"],
            platform_product_id=r["platform_product_id"],
            name=r["name"],
            brand=r["brand"],
            current_price=r["cur_price"] or 0.0,
        )
        for r in rows
    ]


def get_product_history(
    conn: sqlite3.Connection,
    product_id: int,
    days: int = 30,
) -> list[HistoryPoint]:
    cutoff = datetime.now() - timedelta(days=days)
    rows = conn.execute("""
        SELECT price, original_price, discount_rate, in_stock, captured_at
        FROM price_snapshots
        WHERE product_id = ? AND captured_at >= ?
        ORDER BY captured_at ASC
    """, (product_id, cutoff)).fetchall()

    return [
        HistoryPoint(
            captured_at=datetime.fromisoformat(r["captured_at"]),
            price=r["price"],
            original_price=r["original_price"],
            discount_rate=r["discount_rate"],
            in_stock=bool(r["in_stock"]),
        )
        for r in rows
    ]
```

- [ ] **Step 3: Run, commit**
```bash
git add analysis/product_history.py tests/unit/test_product_history.py
git commit -m "feat: add product search and history analysis"
```

---

## Task 7: Commentary Module

**Files:**
- Create: `analysis/commentary.py`
- Test: `tests/unit/test_commentary.py`

- [ ] **Step 1: Write failing test**

`tests/unit/test_commentary.py`:
```python
from datetime import datetime
from analysis.commentary import generate_daily_summary
from analysis.price_changes import PriceChange
from analysis.anomaly import Anomaly


def _pc(brand, name, pct):
    return PriceChange(
        product_id=1, platform_product_id="1", name=name, brand=brand,
        category="kozmetik", old_price=100, new_price=100 * (1 + pct),
        change_amount=100 * pct, change_percent=pct,
        captured_at_old=datetime(2026, 4, 1), captured_at_new=datetime(2026, 4, 7),
        product_url="https://example.com",
    )


def _anom(direction, pct):
    return Anomaly(
        product_id=1, platform_product_id="1", name="x", brand="y",
        category="kozmetik", current_price=80, average_price=100,
        deviation_percent=pct, direction=direction, confidence="high",
        snapshot_count=20, product_url="https://example.com",
    )


def test_summary_includes_count():
    movers = [_pc("Nivea", "krem", -0.25), _pc("Loreal", "ruj", -0.15)]
    anomalies = [_anom("drop", -0.30)]
    summary = generate_daily_summary(movers, anomalies, trend_direction="down")
    assert "2" in summary or "iki" in summary.lower()
    assert "Nivea" in summary


def test_summary_handles_empty_inputs():
    summary = generate_daily_summary([], [], trend_direction="flat")
    assert len(summary) > 10
    assert isinstance(summary, str)


def test_summary_mentions_trend_direction():
    summary = generate_daily_summary([], [], trend_direction="up")
    assert "artış" in summary.lower() or "yukarı" in summary.lower() or "zam" in summary.lower()
```

- [ ] **Step 2: Implement `analysis/commentary.py`**

```python
from typing import Literal
from analysis.price_changes import PriceChange
from analysis.anomaly import Anomaly


_TREND_PHRASE = {
    "down": "genel olarak düşüş",
    "up": "kayda değer artış",
    "flat": "yatay seyir",
}


def generate_daily_summary(
    top_movers: list[PriceChange],
    anomalies: list[Anomaly],
    trend_direction: Literal["up", "down", "flat"],
) -> str:
    """Analiz çıktılarından Türkçe özet paragraf üretir."""
    lines = []

    # Fiyat hareketleri
    if top_movers:
        biggest = top_movers[0]
        direction_word = "indirimi" if biggest.change_percent < 0 else "artışı"
        pct = abs(biggest.change_percent * 100)
        lines.append(
            f"Son 7 günde **{len(top_movers)} üründe** fiyat hareketi tespit edildi. "
            f"En büyük {direction_word} **{biggest.brand or 'bilinmeyen'}** markasında görüldü: "
            f"*{biggest.name[:60]}* → %{pct:.0f} ile {biggest.new_price:.2f} TL."
        )
    else:
        lines.append("Son 7 günde kayda değer fiyat hareketi tespit edilmedi.")

    # Anomaliler
    if anomalies:
        high_conf = [a for a in anomalies if a.confidence == "high"]
        lines.append(
            f"{len(anomalies)} üründe ortalamadan sapma var "
            f"({len(high_conf)} yüksek güvenlikli). Detaylar Anomaliler sayfasında."
        )
    else:
        lines.append("Kategoride anomali tespit edilmedi.")

    # Trend
    lines.append(f"Kategorinin genel fiyat trendi: **{_TREND_PHRASE[trend_direction]}**.")

    return " ".join(lines)
```

- [ ] **Step 3: Run, commit**
```bash
git add analysis/commentary.py tests/unit/test_commentary.py
git commit -m "feat: add template-based daily commentary generator"
```

---

## Task 8: Demo History Seed Script

**Files:**
- Create: `scripts/__init__.py`, `scripts/seed_demo_history.py`

- [ ] **Step 1: Implement seed script**

```python
"""Mevcut ürünlere sentetik 30 günlük fiyat geçmişi ekler (demo amaçlı).

Gerçek veri biriktikçe bu script'e ihtiyaç kalmaz.
"""
import argparse
import random
import sys
from datetime import datetime, timedelta

from config import settings
from storage.database import connect, init_schema


def seed_history(days: int = 30, anomaly_count: int = 3, seed: int = 42):
    random.seed(seed)
    conn = connect(settings.database_path)
    init_schema(conn)

    products = conn.execute(
        "SELECT p.id, s.price FROM products p "
        "JOIN (SELECT product_id, MAX(captured_at) m FROM price_snapshots GROUP BY product_id) latest "
        "ON latest.product_id = p.id "
        "JOIN price_snapshots s ON s.product_id = p.id AND s.captured_at = latest.m"
    ).fetchall()

    if not products:
        print("HATA: Veritabanında ürün yok. Önce 'python main.py' çalıştır.")
        return 1

    # Birkaç ürüne kasıtlı anomali ekle
    anomaly_ids = set(random.sample([p[0] for p in products], min(anomaly_count, len(products))))

    total_inserted = 0
    now = datetime.now()

    for product_id, current_price in products:
        for d in range(days, 0, -1):
            ts = now - timedelta(days=d)
            # Hafif dalgalanma + trend
            variation = random.uniform(-0.05, 0.05)
            price = current_price * (1 + variation)

            # Anomali: ortadaki bir günde %30 düşüş
            if product_id in anomaly_ids and d == 5:
                price = current_price * 0.70

            conn.execute("""
                INSERT INTO price_snapshots (
                    product_id, price, original_price, discount_rate,
                    seller_name, seller_rating, in_stock, captured_at
                ) VALUES (?, ?, NULL, NULL, NULL, NULL, 1, ?)
            """, (product_id, round(price, 2), ts))
            total_inserted += 1

    conn.commit()
    print(f"✓ {len(products)} ürüne {total_inserted} sentetik snapshot eklendi")
    print(f"  ({anomaly_count} ürüne kasıtlı anomali eklendi)")
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--anomalies", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    return seed_history(args.days, args.anomalies, args.seed)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run to verify**
```bash
python scripts/seed_demo_history.py --days 30 --anomalies 3
```

- [ ] **Step 3: Commit**
```bash
git add scripts/
git commit -m "feat: add seed_demo_history script for rich demo data"
```

---

## Task 9: Streamlit Theme + Scaffolding

**Files:**
- Create: `dashboard/.streamlit/config.toml`
- Create: `dashboard/__init__.py`
- Create: `dashboard/app.py` (stub)

- [ ] **Step 1: Create theme**

`dashboard/.streamlit/config.toml`:
```toml
[theme]
primaryColor = "#E85D04"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F8F9FA"
textColor = "#1E1E1E"
font = "sans serif"

[server]
headless = false
runOnSave = true
```

- [ ] **Step 2: Create stub `dashboard/app.py`**

```python
import streamlit as st

st.set_page_config(
    page_title="Metrio",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Metrio")
st.write("Yükleniyor...")
```

- [ ] **Step 3: Verify it runs**
```bash
streamlit run dashboard/app.py
# Ctrl+C to stop
```

- [ ] **Step 4: Commit**
```bash
git add dashboard/
git commit -m "feat: scaffold Streamlit dashboard with brand theme"
```

---

## Task 10: Dashboard Components

**Files:**
- Create: `dashboard/components/__init__.py`, `charts.py`, `cards.py`, `filters.py`, `exports.py`

- [ ] **Step 1: Create `components/__init__.py`** (empty)

- [ ] **Step 2: Create `components/charts.py`**

```python
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def price_history_line(history_df: pd.DataFrame, product_name: str) -> go.Figure:
    fig = px.line(
        history_df,
        x="captured_at",
        y="price",
        title=f"Fiyat Geçmişi: {product_name[:60]}",
        labels={"captured_at": "Tarih", "price": "Fiyat (TL)"},
    )
    fig.update_traces(mode="lines+markers", line=dict(color="#E85D04", width=2))
    fig.update_layout(hovermode="x unified", height=400)
    return fig


def top_discounts_bar(movers) -> go.Figure:
    if not movers:
        return go.Figure()
    df = pd.DataFrame([
        {"urun": f"{m.brand or '-'}: {m.name[:40]}",
         "indirim": abs(m.change_percent * 100),
         "yeni_fiyat": m.new_price}
        for m in movers[:10]
    ])
    fig = px.bar(
        df, x="indirim", y="urun", orientation="h",
        title="En Büyük 10 İndirim (Son 7 Gün)",
        labels={"indirim": "İndirim %", "urun": ""},
        color="indirim", color_continuous_scale=["#FFD4A8", "#E85D04"],
    )
    fig.update_layout(height=500, showlegend=False, yaxis=dict(autorange="reversed"))
    return fig


def trend_line(trend_points, title: str) -> go.Figure:
    df = pd.DataFrame([
        {"tarih": p.date, "ortalama": p.average_price, "median": p.median_price}
        for p in trend_points
    ])
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["tarih"], y=df["ortalama"], name="Ortalama",
                             line=dict(color="#E85D04", width=3)))
    fig.add_trace(go.Scatter(x=df["tarih"], y=df["median"], name="Medyan",
                             line=dict(color="#6C757D", width=2, dash="dash")))
    fig.update_layout(title=title, height=400, xaxis_title="Tarih", yaxis_title="Fiyat (TL)")
    return fig
```

- [ ] **Step 3: Create `components/cards.py`**

```python
import streamlit as st


def summary_row(total_products: int, total_brands: int, last_run: str | None, avg_discount: float | None):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Takip Edilen Ürün", total_products)
    c2.metric("Takip Edilen Marka", total_brands)
    c3.metric("Son Çekim", last_run or "-")
    if avg_discount is not None:
        c4.metric("Ortalama İndirim", f"%{avg_discount * 100:.1f}")
    else:
        c4.metric("Ortalama İndirim", "-")
```

- [ ] **Step 4: Create `components/filters.py`**

```python
import streamlit as st
from datetime import date, timedelta
from analysis.queries import get_unique_brands, get_unique_categories, get_date_range


def sidebar_filters(conn):
    st.sidebar.header("Filtreler")

    categories = get_unique_categories(conn)
    selected_cats = st.sidebar.multiselect("Kategori", categories, default=categories)

    brands = get_unique_brands(conn)
    selected_brands = st.sidebar.multiselect("Marka", brands)

    min_d, max_d = get_date_range(conn)
    default_start = (date.today() - timedelta(days=30))
    date_range = st.sidebar.date_input(
        "Tarih Aralığı",
        value=(default_start, date.today()),
    )

    return {
        "categories": selected_cats,
        "brands": selected_brands,
        "date_range": date_range,
    }
```

- [ ] **Step 5: Create `components/exports.py`**

```python
import pandas as pd
import streamlit as st


def csv_download_button(df: pd.DataFrame, filename: str, label: str = "📥 CSV olarak indir"):
    if df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8-sig")  # BOM for Excel Turkish
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )
```

- [ ] **Step 6: Commit**
```bash
git add dashboard/components/
git commit -m "feat: add dashboard components (charts, cards, filters, exports)"
```

---

## Task 11: Ana Sayfa (Özet)

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Full implementation**

```python
import sqlite3
import streamlit as st

from config import settings
from analysis.queries import get_latest_snapshots_df, get_unique_brands
from analysis.price_changes import top_movers
from analysis.anomaly import detect_anomalies
from analysis.commentary import generate_daily_summary
from dashboard.components.cards import summary_row


st.set_page_config(page_title="Metrio", page_icon="📊", layout="wide")


@st.cache_resource
def get_conn():
    conn = sqlite3.connect(settings.database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@st.cache_data(ttl=300)
def _load_overview():
    conn = get_conn()
    df = get_latest_snapshots_df(conn)
    brands = get_unique_brands(conn)
    movers = top_movers(conn, days=7, direction="both", limit=5)
    anomalies = detect_anomalies(conn, lookback_days=30, threshold_percent=0.20)[:5]

    avg_discount = None
    if "discount_rate" in df.columns:
        non_null = df["discount_rate"].dropna()
        if len(non_null) > 0:
            avg_discount = float(non_null.mean())

    last_run = conn.execute(
        "SELECT MAX(finished_at) FROM run_stats WHERE status='success'"
    ).fetchone()[0]

    trend_direction = "flat"
    if movers:
        down = sum(1 for m in movers if m.change_percent < 0)
        up = sum(1 for m in movers if m.change_percent > 0)
        trend_direction = "down" if down > up else ("up" if up > down else "flat")

    return {
        "df": df,
        "brands": brands,
        "movers": movers,
        "anomalies": anomalies,
        "avg_discount": avg_discount,
        "last_run": last_run,
        "trend_direction": trend_direction,
    }


def main():
    st.title("📊 Metrio")
    st.caption("E-ticaret fiyat istihbaratı — kozmetik kategorisi")

    data = _load_overview()

    if len(data["df"]) == 0:
        st.warning("Henüz veri yok. `python main.py` çalıştırarak veri toplamaya başlayın.")
        return

    summary_row(
        total_products=len(data["df"]),
        total_brands=len(data["brands"]),
        last_run=data["last_run"],
        avg_discount=data["avg_discount"],
    )

    st.divider()

    st.subheader("📝 Günlük Yorum")
    commentary = generate_daily_summary(
        data["movers"],
        data["anomalies"],
        trend_direction=data["trend_direction"],
    )
    st.markdown(commentary)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🎯 En Son 5 Hareket")
        if data["movers"]:
            for m in data["movers"]:
                arrow = "🔻" if m.change_percent < 0 else "🔺"
                pct = abs(m.change_percent * 100)
                st.write(f"{arrow} **{m.brand or '-'}** — {m.name[:50]}")
                st.caption(f"{m.old_price:.2f} → {m.new_price:.2f} TL ({pct:.1f}%)")
        else:
            st.info("Yeterli veri yok. Birkaç gün sonra tekrar kontrol edin.")

    with col2:
        st.subheader("🚨 Son Anomaliler")
        if data["anomalies"]:
            for a in data["anomalies"]:
                emoji = "🔻" if a.direction == "drop" else "🔺"
                pct = abs(a.deviation_percent * 100)
                st.write(f"{emoji} **{a.brand or '-'}** — {a.name[:50]}")
                st.caption(
                    f"{a.current_price:.2f} TL (ortalama {a.average_price:.2f}, "
                    f"%{pct:.0f} sapma, güven: {a.confidence})"
                )
        else:
            st.info("Anomali tespit edilmedi.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Test it manually**
```bash
streamlit run dashboard/app.py
```
Verify ana sayfa 4 kart + yorum + son hareket/anomali listesini gösterir.

- [ ] **Step 3: Commit**
```bash
git add dashboard/app.py
git commit -m "feat: implement dashboard home page with summary and commentary"
```

---

## Task 12: Fırsatlar Sayfası

**Files:**
- Create: `dashboard/pages/2_🎯_Fırsatlar.py`

- [ ] **Step 1: Implementation**

```python
import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.price_changes import top_movers
from dashboard.components.charts import top_discounts_bar
from dashboard.components.exports import csv_download_button


st.set_page_config(page_title="Fırsatlar | Metrio", page_icon="🎯", layout="wide")

st.title("🎯 Fırsatlar — Fiyat Hareketleri")

conn = get_conn()

c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    days = st.slider("Son kaç gün", 1, 30, 7)
with c2:
    direction = st.selectbox("Yön", ["both", "down", "up"],
                             format_func=lambda x: {"both": "Hepsi", "down": "İndirimler", "up": "Zamlar"}[x])
with c3:
    limit = st.number_input("Adet", 5, 100, 20)


@st.cache_data(ttl=60)
def _load(days, direction, limit):
    movers = top_movers(conn, days=days, direction=direction, limit=limit)
    df = pd.DataFrame([
        {
            "Marka": m.brand or "-",
            "Ürün": m.name[:80],
            "Eski": m.old_price,
            "Yeni": m.new_price,
            "Değişim (TL)": m.change_amount,
            "Değişim (%)": m.change_percent * 100,
            "URL": m.product_url,
        } for m in movers
    ])
    return movers, df


movers, df = _load(days, direction, limit)

if movers:
    st.plotly_chart(top_discounts_bar([m for m in movers if m.change_percent < 0]),
                    use_container_width=True)

    st.subheader(f"Tablo — {len(df)} kayıt")
    st.dataframe(
        df,
        column_config={
            "Eski": st.column_config.NumberColumn(format="%.2f TL"),
            "Yeni": st.column_config.NumberColumn(format="%.2f TL"),
            "Değişim (TL)": st.column_config.NumberColumn(format="%.2f"),
            "Değişim (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "URL": st.column_config.LinkColumn("Ürün"),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_download_button(df, f"firsatlar_{days}gun.csv")
else:
    st.info("Seçilen filtreler için fiyat hareketi bulunamadı.")
```

- [ ] **Step 2: Test manually, commit**
```bash
git add "dashboard/pages/2_🎯_Fırsatlar.py"
git commit -m "feat: add Fırsatlar page with filters, chart and CSV export"
```

---

## Task 13: Anomaliler Sayfası

**Files:**
- Create: `dashboard/pages/3_🚨_Anomaliler.py`

- [ ] **Step 1: Implementation**

```python
import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.anomaly import detect_anomalies
from dashboard.components.exports import csv_download_button


st.set_page_config(page_title="Anomaliler | Metrio", page_icon="🚨", layout="wide")

st.title("🚨 Anomaliler — Normalden Sapanlar")
st.caption("Son 30 günün ortalama fiyatından eşiği aşan sapmalar")

conn = get_conn()

c1, c2, c3 = st.columns(3)
with c1:
    threshold = st.slider("Sapma Eşiği (%)", 10, 50, 20) / 100
with c2:
    direction_filter = st.selectbox("Yön", ["all", "drop", "spike"],
        format_func=lambda x: {"all": "Hepsi", "drop": "Düşüş", "spike": "Artış"}[x])
with c3:
    confidence_filter = st.selectbox("Güven", ["all", "high", "medium", "low"],
        format_func=lambda x: {"all": "Hepsi", "high": "Yüksek", "medium": "Orta", "low": "Düşük"}[x])


@st.cache_data(ttl=60)
def _load(threshold):
    return detect_anomalies(conn, lookback_days=30, threshold_percent=threshold)


anomalies = _load(threshold)

if direction_filter != "all":
    anomalies = [a for a in anomalies if a.direction == direction_filter]
if confidence_filter != "all":
    anomalies = [a for a in anomalies if a.confidence == confidence_filter]

if anomalies:
    df = pd.DataFrame([
        {
            "Yön": "🔻 Düşüş" if a.direction == "drop" else "🔺 Artış",
            "Güven": {"high": "🟢 Yüksek", "medium": "🟡 Orta", "low": "🔴 Düşük"}[a.confidence],
            "Marka": a.brand or "-",
            "Ürün": a.name[:80],
            "Güncel": a.current_price,
            "Ortalama": a.average_price,
            "Sapma (%)": a.deviation_percent * 100,
            "Veri Noktası": a.snapshot_count,
            "URL": a.product_url,
        } for a in anomalies
    ])

    st.subheader(f"Tespit edilen sapmalar: {len(df)}")
    st.dataframe(
        df,
        column_config={
            "Güncel": st.column_config.NumberColumn(format="%.2f TL"),
            "Ortalama": st.column_config.NumberColumn(format="%.2f TL"),
            "Sapma (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "URL": st.column_config.LinkColumn("Ürün"),
        },
        hide_index=True,
        use_container_width=True,
    )

    csv_download_button(df, "anomaliler.csv")
else:
    st.info("Seçilen kriterlerde anomali bulunamadı. Eşiği düşürebilir veya daha fazla veri toplayabilirsiniz.")
```

- [ ] **Step 2: Commit**
```bash
git add "dashboard/pages/3_🚨_Anomaliler.py"
git commit -m "feat: add Anomaliler page with threshold and confidence filters"
```

---

## Task 14: Trendler Sayfası

**Files:**
- Create: `dashboard/pages/4_📈_Trendler.py`

- [ ] **Step 1: Implementation**

```python
import streamlit as st

from dashboard.app import get_conn
from analysis.queries import get_unique_brands, get_unique_categories
from analysis.trends import brand_trend, category_trend
from dashboard.components.charts import trend_line


st.set_page_config(page_title="Trendler | Metrio", page_icon="📈", layout="wide")

st.title("📈 Trendler — Zaman İçinde Fiyat Eğilimi")

conn = get_conn()

mode = st.radio("Gruplama", ["Marka", "Kategori"], horizontal=True)
days = st.slider("Son kaç gün", 7, 90, 30)

if mode == "Marka":
    brands = get_unique_brands(conn)
    if not brands:
        st.warning("Henüz marka verisi yok.")
        st.stop()
    selected = st.multiselect("Markalar (2-3 tane karşılaştırılabilir)",
                              brands, default=brands[:1], max_selections=3)
    if not selected:
        st.info("En az bir marka seçin.")
        st.stop()

    for b in selected:
        points = brand_trend(conn, brand=b, days=days)
        if points:
            st.plotly_chart(trend_line(points, f"{b} — Ortalama Fiyat"), use_container_width=True)
        else:
            st.info(f"'{b}' için yeterli veri yok.")

else:
    cats = get_unique_categories(conn)
    if not cats:
        st.warning("Henüz kategori verisi yok.")
        st.stop()
    selected_cat = st.selectbox("Kategori", cats)

    points = category_trend(conn, category=selected_cat, days=days)
    if points:
        st.plotly_chart(trend_line(points, f"{selected_cat.title()} — Ortalama Fiyat"), use_container_width=True)
    else:
        st.info("Yeterli veri yok.")
```

- [ ] **Step 2: Commit**
```bash
git add "dashboard/pages/4_📈_Trendler.py"
git commit -m "feat: add Trendler page with brand/category time-series"
```

---

## Task 15: Ürün Detay Sayfası

**Files:**
- Create: `dashboard/pages/5_🔍_Ürün_Detay.py`

- [ ] **Step 1: Implementation**

```python
import pandas as pd
import streamlit as st

from dashboard.app import get_conn
from analysis.product_history import search_products, get_product_history
from dashboard.components.charts import price_history_line
from dashboard.components.exports import csv_download_button


st.set_page_config(page_title="Ürün Detay | Metrio", page_icon="🔍", layout="wide")

st.title("🔍 Ürün Detay & Arama")

conn = get_conn()

query = st.text_input("Ürün veya marka ara", placeholder="Örn: nemlendirici, loreal, güneş kremi")

if query:
    results = search_products(conn, query, limit=20)
    if not results:
        st.info("Eşleşen ürün bulunamadı.")
        st.stop()

    labels = {r.product_id: f"{r.brand or '-'} — {r.name[:70]} ({r.current_price:.2f} TL)"
              for r in results}
    selected_id = st.selectbox("Ürün seç", list(labels.keys()),
                               format_func=lambda k: labels[k])

    if selected_id:
        days = st.slider("Geçmiş (gün)", 7, 90, 30)
        history = get_product_history(conn, selected_id, days=days)

        if not history:
            st.warning("Bu ürün için henüz geçmiş veri yok.")
        else:
            product = next(r for r in results if r.product_id == selected_id)

            c1, c2, c3 = st.columns(3)
            prices = [h.price for h in history]
            c1.metric("Güncel Fiyat", f"{history[-1].price:.2f} TL")
            c2.metric("En Düşük (30g)", f"{min(prices):.2f} TL")
            c3.metric("En Yüksek (30g)", f"{max(prices):.2f} TL")

            df = pd.DataFrame([
                {"captured_at": h.captured_at, "price": h.price,
                 "original_price": h.original_price, "discount_rate": h.discount_rate,
                 "in_stock": h.in_stock}
                for h in history
            ])
            st.plotly_chart(price_history_line(df, product.name), use_container_width=True)

            with st.expander("Ham veri tablosu"):
                st.dataframe(df, hide_index=True, use_container_width=True)

            csv_download_button(df, f"urun_{selected_id}_gecmis.csv")

else:
    st.info("Yukarıdan ürün adı veya marka arayın.")
```

- [ ] **Step 2: Commit**
```bash
git add "dashboard/pages/5_🔍_Ürün_Detay.py"
git commit -m "feat: add product detail page with search and price history"
```

---

## Task 16: Final Polish + README Update

- [ ] **Step 1: Run full test suite**
```bash
pytest
```
Expected: ~80+ tests passing.

- [ ] **Step 2: Seed demo data**
```bash
python scripts/seed_demo_history.py --days 30 --anomalies 3
```

- [ ] **Step 3: Launch dashboard and smoke-test all 5 pages**
```bash
streamlit run dashboard/app.py
```

- [ ] **Step 4: Update README**

Append to `README.md`:
```markdown
## Dashboard (Hafta 2)

### Çalıştırma
```bash
streamlit run dashboard/app.py
```
Tarayıcıda `http://localhost:8501` açılır.

### Sayfalar
- **Özet** — Genel durum, günlük yorum, son hareketler/anomaliler
- **Fırsatlar** — En büyük fiyat hareketleri, filtre + CSV indir
- **Anomaliler** — Normalden sapan fiyatlar, eşik ayarlanabilir
- **Trendler** — Marka/kategori zaman serisi
- **Ürün Detay** — Arama + tek ürün fiyat geçmişi

### Demo Verisi
Gerçek veri biriktirilene kadar demo için:
```bash
python scripts/seed_demo_history.py --days 30
```
Mevcut ürünlere 30 gün sentetik geçmiş ekler.
```

- [ ] **Step 5: Commit**
```bash
git add README.md
git commit -m "docs: add dashboard usage to README"
```
