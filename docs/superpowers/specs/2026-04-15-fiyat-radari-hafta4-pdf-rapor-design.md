# Fiyat Radarı — Hafta 4: Haftalık PDF Raporu

**Tarih:** 2026-04-15
**Durum:** Onaylandı, implementasyona hazır

## Amaç

Müşteriye e-posta ile gönderilebilecek, fiziksel çıktı alınabilecek bir haftalık özet raporu üretmek. Dashboard'a bağımlılığı azaltır, "profesyonel hizmet" algısı sağlar.

Tek komut ile PDF üretilir:
```
python scripts/generate_report.py --days 7
```

Çıktı: `reports/fiyat_radari_2026-04-15.pdf` (5-6 sayfa).

## Kapsam dışı (YAGNI)

- E-posta gönderimi (Hafta 5'e).
- Müşteri bazlı şablon (tek genel şablon şimdilik, multi-tenant Hafta 5+).
- Interaktif PDF öğeleri.
- HTML/PowerPoint export.

## İçerik (sayfalar)

1. **Kapak** — başlık "Fiyat Radarı — Haftalık Rapor", dönem tarihi, üretim tarihi.
2. **Özet** — toplam ürün sayısı, izlenen marka sayısı, toplam anomali, top 3 fırsat.
3. **En Büyük Fiyat Hareketleri** — top 10 tablo (marka, ürün, eski/yeni fiyat, değişim %, URL).
4. **Anomaliler** — %20+ sapma tablosu (marka, ürün, güncel, ortalama, sapma %, güven).
5. **Marka Trendi** — en aktif 3 markanın ortalama fiyat zaman serisi grafiği.
6. **Tam Ürün Listesi** — ek; tüm izlenen ürünler (marka, ürün adı, güncel fiyat).

## Mimari

```
reports/
  __init__.py
  builder.py        # ReportBuilder — sayfa ekleme akışını yöneten sınıf
  sections.py       # Her sayfa için saf fonksiyon: Flowable listesi döner
  charts.py         # matplotlib ile PNG üret → ReportLab Image flowable
scripts/
  generate_report.py  # CLI giriş noktası
```

### `reports/sections.py`

Her fonksiyon `(conn, params) -> list[Flowable]` imzasında:
- `build_cover(date_from, date_to) -> list[Flowable]`
- `build_summary(conn, days) -> list[Flowable]`
- `build_top_movers(conn, days, limit=10) -> list[Flowable]`
- `build_anomalies(conn, threshold=0.20) -> list[Flowable]`
- `build_brand_trend(conn, days) -> list[Flowable]`
- `build_product_list(conn) -> list[Flowable]`

Her biri hata durumunda bile bir başlık + "veri yok" açıklaması döner (boş liste döndürmez), PDF'in tutarlı görünmesi için.

### `reports/charts.py`

- `brand_trend_chart(conn, days, top_n=3) -> bytes` — PNG bytes döner, ReportLab `Image`'a verilir.
- Matplotlib headless (`Agg` backend) kullanır.

### `reports/builder.py`

```python
class ReportBuilder:
    def __init__(self, output_path: Path, title: str): ...
    def add_section(self, flowables: list[Flowable]): ...
    def add_page_break(self): ...
    def build(self): ...  # ReportLab SimpleDocTemplate ile PDF yazar
```

### `scripts/generate_report.py`

```
python scripts/generate_report.py --days 7 [--output reports/] [--category kozmetik]
```

- `--days` (int, default 7) — lookback penceresi
- `--output` (path, default `reports/`) — çıktı dizini (yoksa oluşturulur)
- `--category` (str, opsiyonel) — şimdilik sadece metadata olarak kullanılır (tek kategori var)

Çıktı dosya adı: `fiyat_radari_{YYYY-MM-DD}.pdf` (çalıştırılan günün tarihi).

## Stil

- Ana renk: `#E85D04` (dashboard ile uyum).
- Başlık fontu: Helvetica-Bold 18pt.
- Tablo: ReportLab Table + TableStyle, zebra-striped.
- Sayfa altına footer: "Fiyat Radarı · {tarih}".
- A4 dikey, 15mm marjin.

## Hata yönetimi

- Dizin yok: otomatik oluştur (`output_dir.mkdir(parents=True, exist_ok=True)`).
- Veritabanı yok: script exit code 1, kullanıcıya hata mesajı.
- Chart oluşturulamazsa (matplotlib hatası): log WARNING, o sayfada "Grafik oluşturulamadı" metni görünür.
- Yeterli veri yoksa (ör. 0 top mover): tablo yerine "Bu dönemde hareket tespit edilmedi" metni.

## Testler

### Unit (`tests/unit/test_report_sections.py`)
- `build_cover` 2+ flowable döner, başlık metni içerir.
- `build_summary` in-memory DB ile çağrılır → beklenen rakamlar flowable içeriğinde.
- `build_top_movers` seed verisi → table flowable sayısı doğru, URL sütunu var.
- `build_anomalies` eşik altı hareket → "anomali yok" mesajı.
- `build_brand_trend` 0 marka → "veri yok".

### Integration (`tests/integration/test_report_build.py`)
- Seed edilmiş in-memory DB → `generate_report(conn, output_path, days=7)` → dosya var ve > 5KB.
- Dizin yoksa oluşturur.

### Manuel
- Gerçek veritabanı ile `python scripts/generate_report.py --days 30` çalıştır, PDF'i aç, göz kontrolü.

## Kullanıcı kurulum akışı

README'ye eklenir:

1. Bağımlılıklar yüklü (`pip install -r requirements.txt` yeterli, yeni kütüphaneler eklendi).
2. `python scripts/generate_report.py --days 7` çalıştır.
3. `reports/fiyat_radari_2026-04-15.pdf` aç.

## Bağımlılıklar

`requirements.txt`'e:
```
reportlab==4.2.5
matplotlib==3.9.2
```

Not: `matplotlib` zaten dolaylı olarak pandas ile bir sürüme gelebilir, ama direkt bağımlılık olarak eklemeliyiz.

## Kabul kriterleri

- [ ] `python scripts/generate_report.py --days 7` `reports/fiyat_radari_YYYY-MM-DD.pdf` üretir.
- [ ] PDF 5-6 sayfa, kapak + özet + movers + anomaliler + trend + liste içerir.
- [ ] Tüm unit+integration testler geçer.
- [ ] Boş veri durumunda bile PDF üretilir (sayfalar "veri yok" ile doldurulur).
- [ ] README'de kullanım adımları var.
