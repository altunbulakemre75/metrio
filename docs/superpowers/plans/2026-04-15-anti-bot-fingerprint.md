# Anti-Bot: Fingerprint + Proxy Pool Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development. Checkbox (`- [ ]`) syntax.

**Goal:** Fingerprint rotation (UA + viewport + locale) + rastgele gecikme (1-3s) + proxy pool altyapısı (disabled default). Scraper'lar hafif bot kontrollerine karşı dirençli olur.

**Architecture:** `utils/fingerprint.py` ve `utils/proxy_pool.py` yeni; `utils/rate_limiter.py`'a `jitter_delay` decorator'ı eklenir; `config.py` 4 yeni alan alır; iki scraper entegrasyonu.

**Tech Stack:** Python 3.13, Playwright, pytest

---

### Task 1: Config genişletme

**Files:**
- Modify: `config.py`
- Modify: `.env.example`

- [ ] **Step 1: `config.py`'a 4 alan ekle**

`Settings` sınıfına şunları ekle (`scraper_requests_per_second`'ın altına):

```python
    scraper_min_delay: float = Field(default=1.0, gt=0)
    scraper_max_delay: float = Field(default=3.0, gt=0)
    proxy_enabled: bool = False
    proxy_list: str = ""
```

- [ ] **Step 2: `.env.example`'a ekle**

`SCRAPER_REQUESTS_PER_SECOND=1.0` satırının altına:

```
SCRAPER_MIN_DELAY=1.0
SCRAPER_MAX_DELAY=3.0
PROXY_ENABLED=false
PROXY_LIST=
```

- [ ] **Step 3: Doğrula**

Run: `python -c "from config import settings; print(settings.scraper_min_delay, settings.proxy_enabled)"`
Expected: `1.0 False`

- [ ] **Step 4: Commit**

```bash
git add config.py .env.example
git commit -m "feat: add anti-bot config fields (jitter delay + proxy)"
```

---

### Task 2: Fingerprint

**Files:**
- Create: `utils/fingerprint.py`
- Create: `tests/unit/test_fingerprint.py`

- [ ] **Step 1: Failing test**

`tests/unit/test_fingerprint.py`:

```python
from utils.fingerprint import get_fingerprint, _USER_AGENTS, _VIEWPORTS, _LOCALES


def test_get_fingerprint_has_all_keys():
    fp = get_fingerprint()
    assert "user_agent" in fp
    assert "viewport" in fp
    assert "locale" in fp


def test_user_agent_from_pool():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["user_agent"] in _USER_AGENTS


def test_viewport_is_valid_dict():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["viewport"] in _VIEWPORTS
        assert fp["viewport"]["width"] > 0
        assert fp["viewport"]["height"] > 0


def test_locale_from_pool():
    for _ in range(50):
        fp = get_fingerprint()
        assert fp["locale"] in _LOCALES


def test_pool_sizes():
    assert len(_USER_AGENTS) >= 10
    assert len(_VIEWPORTS) >= 5
    assert len(_LOCALES) >= 3


def test_randomness_produces_variety():
    seen_uas = set()
    for _ in range(200):
        seen_uas.add(get_fingerprint()["user_agent"])
    # 10 UA, 200 çağrı → en az 5 farklı görülmeli (olasılıksal ama güvenli)
    assert len(seen_uas) >= 5
```

- [ ] **Step 2: Testin fail ettiğini doğrula**

Run: `pytest tests/unit/test_fingerprint.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: `utils/fingerprint.py` oluştur**

```python
"""Rastgele tarayıcı fingerprint üretimi — bot tespitine karşı."""
import random


_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
]

_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1680, "height": 1050},
]

_LOCALES = ["tr-TR", "en-US", "en-GB"]


def get_fingerprint() -> dict:
    """Rastgele ua + viewport + locale kombinasyonu döner."""
    return {
        "user_agent": random.choice(_USER_AGENTS),
        "viewport": random.choice(_VIEWPORTS),
        "locale": random.choice(_LOCALES),
    }
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/unit/test_fingerprint.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add utils/fingerprint.py tests/unit/test_fingerprint.py
git commit -m "feat: add browser fingerprint rotation"
```

---

### Task 3: Proxy Pool

**Files:**
- Create: `utils/proxy_pool.py`
- Create: `tests/unit/test_proxy_pool.py`

- [ ] **Step 1: Failing test**

`tests/unit/test_proxy_pool.py`:

```python
from utils.proxy_pool import ProxyPool


def test_disabled_returns_none():
    pool = ProxyPool(proxy_list="http://u:p@1.2.3.4:8080", enabled=False)
    assert pool.pick() is None


def test_enabled_but_empty_returns_none():
    pool = ProxyPool(proxy_list="", enabled=True)
    assert pool.pick() is None


def test_enabled_with_single_proxy():
    pool = ProxyPool(proxy_list="http://user:pass@1.2.3.4:8080", enabled=True)
    result = pool.pick()
    assert result is not None
    assert result["server"] == "http://1.2.3.4:8080"
    assert result["username"] == "user"
    assert result["password"] == "pass"


def test_enabled_rotates_multiple_proxies():
    pool = ProxyPool(
        proxy_list="http://u1:p1@1.1.1.1:80,http://u2:p2@2.2.2.2:80",
        enabled=True,
    )
    picks = {pool.pick()["server"] for _ in range(50)}
    assert len(picks) == 2  # ikisinden de seçilmeli


def test_proxy_without_auth():
    pool = ProxyPool(proxy_list="http://1.2.3.4:8080", enabled=True)
    result = pool.pick()
    assert result["server"] == "http://1.2.3.4:8080"
    assert result["username"] == ""
    assert result["password"] == ""
```

- [ ] **Step 2: Testin fail ettiğini doğrula**

Run: `pytest tests/unit/test_proxy_pool.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: `utils/proxy_pool.py` oluştur**

```python
"""Proxy rotasyonu — Playwright context'ine verilecek proxy config üretir."""
import random
from urllib.parse import urlparse


class ProxyPool:
    """Virgülle ayrılmış proxy listesinden rastgele seçer.

    Disabled modda veya boş listede None döner — scraper proxy kullanmaz.
    """

    def __init__(self, proxy_list: str, enabled: bool):
        self.enabled = enabled
        self.proxies: list[str] = (
            [p.strip() for p in proxy_list.split(",") if p.strip()]
            if proxy_list else []
        )

    def pick(self) -> dict | None:
        if not self.enabled or not self.proxies:
            return None
        url = random.choice(self.proxies)
        parsed = urlparse(url)
        return {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username or "",
            "password": parsed.password or "",
        }
```

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `pytest tests/unit/test_proxy_pool.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add utils/proxy_pool.py tests/unit/test_proxy_pool.py
git commit -m "feat: add proxy pool (disabled by default)"
```

---

### Task 4: Jitter Delay

**Files:**
- Modify: `utils/rate_limiter.py`
- Modify: `tests/unit/test_rate_limiter.py`

- [ ] **Step 1: Mevcut test dosyasını oku**

Run: `cat tests/unit/test_rate_limiter.py` — mevcut testleri anla.

- [ ] **Step 2: Yeni failing test ekle**

`tests/unit/test_rate_limiter.py` sonuna ekle:

```python
import time
from utils.rate_limiter import jitter_delay


def test_jitter_delay_waits_within_range():
    calls = []

    @jitter_delay(min_seconds=0.01, max_seconds=0.03)
    def fn():
        calls.append(time.monotonic())

    t0 = time.monotonic()
    fn()
    fn()
    elapsed = calls[1] - calls[0]
    # 2 çağrı arası ~10-30ms bekleme
    assert 0.01 <= elapsed <= 0.1


def test_jitter_delay_returns_function_value():
    @jitter_delay(0.001, 0.002)
    def fn(x):
        return x * 2
    assert fn(5) == 10
```

- [ ] **Step 3: `utils/rate_limiter.py`'a ekle**

Dosyanın sonuna ekle:

```python
import random


def jitter_delay(min_seconds: float, max_seconds: float):
    """Her çağrıdan önce uniform(min, max) saniye bekler."""
    if min_seconds < 0 or max_seconds < min_seconds:
        raise ValueError("geçersiz jitter aralığı")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(random.uniform(min_seconds, max_seconds))
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

Run: `pytest tests/unit/test_rate_limiter.py -v`
Expected: tüm eski + 2 yeni PASS

- [ ] **Step 5: Commit**

```bash
git add utils/rate_limiter.py tests/unit/test_rate_limiter.py
git commit -m "feat: add jitter_delay decorator for randomized request spacing"
```

---

### Task 5: Scraper Entegrasyonu

**Files:**
- Modify: `scrapers/trendyol.py`
- Modify: `scrapers/hepsiburada.py`

- [ ] **Step 1: `scrapers/trendyol.py` — import + rate_limit değiştir**

Import bloğuna ekle:

```python
from utils.fingerprint import get_fingerprint
from utils.proxy_pool import ProxyPool
from utils.rate_limiter import rate_limit, jitter_delay
```

`_load_page` decorator'ını değiştir — `rate_limit` yerine `jitter_delay`:

```python
    @jitter_delay(settings.scraper_min_delay, settings.scraper_max_delay)
    @retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
    def _load_page(self, page: Page, url: str) -> str:
        log.info(f"Sayfa yükleniyor: {url}")
        page.goto(url, wait_until="networkidle", timeout=45000)
        self._scroll_to_load(page)
        return page.content()
```

- [ ] **Step 2: `TrendyolScraper.__init__` — proxy pool ekle**

```python
    def __init__(self):
        self._playwright = None
        self._browser: Browser | None = None
        self._proxy_pool = ProxyPool(settings.proxy_list, settings.proxy_enabled)
```

- [ ] **Step 3: `fetch_category` — context'i fingerprint ile oluştur**

`browser.new_context(user_agent=settings.scraper_user_agent)` satırını değiştir:

```python
            fp = get_fingerprint()
            ctx_args = {
                "user_agent": fp["user_agent"],
                "viewport": fp["viewport"],
                "locale": fp["locale"],
            }
            proxy = self._proxy_pool.pick()
            if proxy:
                ctx_args["proxy"] = proxy
            context = browser.new_context(**ctx_args)
```

- [ ] **Step 4: `scrapers/hepsiburada.py` — aynı 3 değişiklik**

Trendyol ile birebir aynı pattern (import, __init__, fetch_category).

- [ ] **Step 5: Tüm testleri çalıştır**

Run: `pytest --tb=short -q`
Expected: 146 passed, 1 deselected (137 önceki + 13 yeni bot fingerprint/proxy/jitter)

- [ ] **Step 6: Commit**

```bash
git add scrapers/trendyol.py scrapers/hepsiburada.py
git commit -m "feat: integrate fingerprint rotation + jitter delay into scrapers"
```

---

### Task 6: Canlı Doğrulama

- [ ] **Step 1: `python main.py` çalıştır**

Run: `python main.py`
Expected: 4 kategori başarılı, fingerprint rotasyonu iç detay (log'a yansımaz).

- [ ] **Step 2: Final commit**

Değişiklik varsa.

---

## Self-Review

- **Spec coverage:** fingerprint ✅, proxy_pool ✅, jitter_delay ✅, config ✅, scraper entegrasyonu ✅
- **Type consistency:** `get_fingerprint() -> dict`, `ProxyPool.pick() -> dict | None`, `jitter_delay(float, float)` tüm tasklarda aynı
- **Regression:** Mevcut testler `rate_limit` yerine `jitter_delay` kullanan kodu dolaylı test eder — `test_rate_limiter.py` `rate_limit`'i hâlâ test eder (geriye uyum)
- **Placeholder yok.**
