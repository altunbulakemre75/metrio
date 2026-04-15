# Metrio — Anti-Bot: Fingerprint + Proxy Pool

**Tarih:** 2026-04-15
**Durum:** Onaylandı

## Amaç

Scraper'ları hafif bot kontrollerinden korumak için:
- User-agent, viewport, locale rastgele kombinasyonları (fingerprint rotation)
- İstekler arası rastgele gecikme (deterministik 1/s yerine 1-3s jitter)
- Proxy altyapısını kod olarak hazırla ama pasif tut (müşteri geldiğinde proxy servisi alınır, config'ten açılır)

Hepsiburada/Amazon gibi agresif bot korumalarını tek başına aşmaz — residential proxy gerekir. Bu çalışma proxy'ye *hazır* bir zemin kurar.

## Kapsam dışı

- Gerçek proxy servisi entegrasyonu (Smartproxy/BrightData API) — müşteri aşamasında
- CAPTCHA çözücü
- Mouse hareketi simülasyonu / stealth.js
- Platform başına farklı stratejiler (tek global fingerprint yeterli)

## Mimari

```
utils/
  fingerprint.py         # yeni — get_fingerprint() -> dict
  proxy_pool.py          # yeni — ProxyPool sınıfı
  rate_limiter.py        # güncel — jitter desteği
config.py                # +4 alan
scrapers/trendyol.py     # fetch_category fingerprint/proxy kullanır
scrapers/hepsiburada.py  # fetch_category fingerprint/proxy kullanır
tests/unit/
  test_fingerprint.py    # yeni
  test_proxy_pool.py     # yeni
  test_rate_limiter.py   # yeni test eklenir
```

### `utils/fingerprint.py`

```python
_USER_AGENTS = [
    # 10 gerçek Chrome UA (Windows 10/11, macOS) — rotate
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
    """Rastgele ua+viewport+locale döner."""
    return {
        "user_agent": random.choice(_USER_AGENTS),
        "viewport": random.choice(_VIEWPORTS),
        "locale": random.choice(_LOCALES),
    }
```

### `utils/proxy_pool.py`

```python
class ProxyPool:
    def __init__(self, proxy_list: str, enabled: bool):
        self.enabled = enabled
        self.proxies = [p.strip() for p in proxy_list.split(",") if p.strip()] if proxy_list else []

    def pick(self) -> dict | None:
        """Playwright proxy config'i döner, yoksa None."""
        if not self.enabled or not self.proxies:
            return None
        url = random.choice(self.proxies)
        # http://user:pass@host:port → Playwright formatı
        parsed = urlparse(url)
        return {
            "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}",
            "username": parsed.username or "",
            "password": parsed.password or "",
        }
```

### `utils/rate_limiter.py`

Mevcut `@rate_limit(calls_per_second=N)` korunur (geriye dönük uyum). Yeni bir decorator eklenir:

```python
def jitter_delay(min_seconds: float, max_seconds: float):
    """Her çağrıdan önce uniform(min, max) saniye bekler."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            time.sleep(random.uniform(min_seconds, max_seconds))
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

### Scraper entegrasyonu

`TrendyolScraper._load_page` decorator'ı değişir:

```python
@jitter_delay(settings.scraper_min_delay, settings.scraper_max_delay)
@retry(max_attempts=3, backoff_base=2, exceptions=(Exception,))
def _load_page(self, page: Page, url: str) -> str:
    ...
```

`fetch_category` context oluşturmadan önce fingerprint çeker:

```python
def fetch_category(self, category_url, max_products=500):
    browser = self._ensure_browser()
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
    ...
```

`__init__` değişir:

```python
def __init__(self):
    self._playwright = None
    self._browser: Browser | None = None
    self._proxy_pool = ProxyPool(settings.proxy_list, settings.proxy_enabled)
```

`HepsiburadaScraper` aynı değişiklikleri alır.

### Config (`config.py`)

```python
scraper_min_delay: float = Field(default=1.0, gt=0)
scraper_max_delay: float = Field(default=3.0, gt=0)
proxy_enabled: bool = False
proxy_list: str = ""
```

`.env.example`:
```
SCRAPER_MIN_DELAY=1.0
SCRAPER_MAX_DELAY=3.0
PROXY_ENABLED=false
PROXY_LIST=
```

## Testler

### Unit

- `test_fingerprint.py` — 100 çağrı → hepsinde geçerli dict, her üç anahtarı olan
- `test_proxy_pool.py`:
  - disabled → `None`
  - enabled + empty list → `None`
  - enabled + 2 proxy → `pick()` bunlardan biri döner, format doğru
- `test_rate_limiter.py` — yeni: `jitter_delay(0.01, 0.02)` ~15ms bekler (tolerans)

### Regression

Mevcut 137 test çalışmaya devam etmeli — `extract_cards_from_page` değişmiyor, `TrendyolScraper` mimarisi korunuyor.

## Kabul kriterleri

- [ ] `python main.py` eskisi gibi çalışır, fingerprint rotate eder (log'a yansımaz, iç detay)
- [ ] PROXY_ENABLED=false (varsayılan) → hiçbir proxy kullanılmaz
- [ ] `scraper_min_delay/max_delay` env'den okunur, `time.sleep` bu aralıkta
- [ ] Tüm eski testler geçer, yeni testler de geçer (~145 toplam)
