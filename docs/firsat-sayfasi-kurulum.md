# Fırsat Sayfası — Kurulum Rehberi

Kozmetik indirimlerini her gün otomatik olarak Instagram'a (kaydırmalı gönderi) ve
Telegram kanalına (ürün başına fotoğraf + link) paylaşan sistem. Kod: `deals/`.

## Nasıl çalışıyor?

| Saat | Görev | Ne yapar |
|---|---|---|
| 03:00 | Metrio Daily Scrape | Trendyol / Akakçe kategorilerini tarar |
| 10:00, 14:00, 19:00 | Metrio Deals Post | `python -m deals.run` |

Her paylaşımda:

1. **Seçim:** Son 36 saatte taranmış, stokta olan kozmetik/parfüm/vitamin/cilt bakımı ürünleri.
   - En az %30 indirimli (üstü çizili fiyata göre) **ya da** son 7 gün içindeki önceki fiyatından en az %15 düşmüş olmalı.
   - Gerçek fiyat düşüşü, satıcının yazdığı indirimden 2 kat değerli sayılır.
   - En az 5 günlük geçmişi varken fiyatı son 30 günün en düşüğüyse karta "SON 30 GÜNÜN EN DÜŞÜK FİYATI" yazılır.
   - Aynı markadan en fazla 2 ürün; son 14 günde paylaşılan ürün tekrar paylaşılmaz.
   - Adında "deterjan, çamaşır, bulaşık, yumuşatıcı" geçenler elenir (`DEALS_EXCLUDE_WORDS`).
2. **Kartlar:** 1 kapak + 5 ürün kartı, 1080x1350 JPEG → `data/deals/<tarih-saat>/`.
3. **Telegram kanalı:** Her ürün için kart + fiyat + link.
4. **Instagram:** Kartlar `github.com/altunbulakemre75/firsat-gorselleri` reposuna push edilir
   (Instagram görseli internetten kendisi indiriyor), sonra tek kaydırmalı gönderi atılır.
5. Bir şey ters giderse yönetici Telegram sohbetine (`TELEGRAM_CHAT_ID`) uyarı gelir.

Fırsat 3'ten azsa paylaşım yapılmaz (genelde gece taraması çalışmamıştır).

---

## Senin yapacakların

Tüm ayarlar `.env` dosyasında, "Fırsat sayfası" bölümünde. Her adımdan sonra kontrol et:

```
.venv\Scripts\python.exe -m deals.run --check
```

### 1. Sayfa adı

`.env` → `DEALS_PAGE_NAME=...` (kartların sol üstünde yazar). Şu an yer tutucu: "Fırsat Radarı".

### 2. Telegram kanalı

1. Telegram → Yeni Kanal → herkese açık, bir kullanıcı adı ver (örn. `@kozmetikfirsat`).
2. Kanal ayarları → Yöneticiler → `@metrio_price_bot`'u ekle, "Mesaj gönderme" izni açık olsun.
3. `.env` → `TELEGRAM_CHANNEL_ID=@kozmetikfirsat`
4. `--check` → `OK    Telegram kanalı: <kanal adı>` görmelisin.

### 3. Instagram

> Meta panelindeki menü adları zaman zaman değişiyor; aşağıdaki adlar yaklaşık.

1. **Hesap:** Instagram hesabını aç → Ayarlar → Hesap türü ve araçlar →
   **Profesyonel hesaba geç** (İçerik üreticisi ya da İşletme). Facebook sayfası gerekmiyor.
2. **Meta uygulaması:** developers.facebook.com → kişisel Facebook hesabınla giriş yap →
   My Apps → **Create App**. Kullanım alanı: **Manage messaging & content on Instagram**.
   (Uygulama adında "Instagram", "IG", "Facebook", "Meta" geçemez.)
3. Use cases → Customize → **Permissions and features**: `instagram_business_basic` ve
   `instagram_business_content_publish` → **Add**. (`instagram_basic` / `instagram_content_publish`
   değil; doğrularında "business" geçer.)
4. Soldan **API setup with Unified login** (2026-11 itibarıyla adı bu; eski adı "Instagram login"):
   - **İşletme portföyü** ister → "+ İş portföyü" → yeni portföy oluştur ve bağla.
   - **Create new configuration** → varsayılanlarla kaydet (System-user token, süresi yok).
     Redirect URL / Login URL / Webhooks boş kalır.
   - App roles → Roles → Add people → **Instagram Tester** → Instagram kullanıcı adı.
     Daveti bilgisayardan kabul et: instagram.com/accounts/manage_access/ → Tester invites.
   - **2. Generate access tokens** → Add account → Instagram ile giriş → hesap ID'si görünür →
     **Generate token**.
5. `.env`'ye yaz (anahtarı kimseye gönderme; doğrudan dosyaya yapıştır):
   ```
   INSTAGRAM_ENABLED=true
   INSTAGRAM_USER_ID=<hesap ID>
   INSTAGRAM_ACCESS_TOKEN=<anahtar>
   ```
6. `--check` → `OK    Instagram hesabı: @kullaniciadi (id ...)`.

Bu yol `EAA…` ile başlayan, **süresi dolmayan** bir sistem anahtarı verir; sistem bunu
graph.facebook.com üzerinden kullanır ve yenilemez. Eski "Instagram ile Giriş" anahtarı
(`IGAA…`, 60 gün) da çalışır: o durumda graph.instagram.com kullanılır, haftada bir
yenilenip `data/instagram_token.json`'a yazılır. Kendi hesabın uygulamada test kullanıcısı
olduğu için uygulama incelemesine (App Review) gerek kalmaz.

### 4. İlk deneme

```
.venv\Scripts\python.exe -m deals.run --dry-run
```
Sadece kartları üretir (`data/deals/` altında), hiçbir yere göndermez. Beğenirsen:

```
.venv\Scripts\python.exe -m deals.run
```
Gerçek paylaşım. Sonrası otomatik (10:00 / 14:00 / 19:00).

---

## Ayarlar

| Ayar | Varsayılan | Anlamı |
|---|---|---|
| `DEALS_PAGE_NAME` | Fırsat Radarı | Kartlardaki sayfa adı |
| `DEALS_CATEGORIES` | kozmetik,parfum,vitamin,cilt-bakimi | Taranan kategori adları (`.env`'de `canta` da var) |
| `DEALS_CATEGORY_CAPS` | (boş) | Paylaşım başına kategori sınırı, örn. `canta:2` |
| `DEALS_PER_POST` | 5 | Paylaşım başına ürün |
| `DEALS_MIN_DISCOUNT` | 0.30 | En düşük indirim oranı |
| `DEALS_EXCLUDE_WORDS` | deterjan,çamaşır,bulaşık,yumuşatıcı | Ada göre elenen ürünler |
| `DEALS_REPEAT_AFTER_DAYS` | 14 | Aynı ürün en erken kaç gün sonra tekrar |
| `DEALS_CAPTION_FOOTER` | Ürün linkleri Telegram kanalımızda… | Instagram açıklamasının sonu |
| `DEALS_HASHTAGS` | #indirim #kozmetik … | Instagram etiketleri (en fazla 30) |
| `IMAGE_HOST_REPO_DIR` | C:/Users/altun/firsat-gorselleri | Görsel reposunun bilgisayardaki kopyası |
| `IMAGE_HOST_BASE_URL` | https://raw.githubusercontent.com/… | Görsellerin herkese açık adresi |

Görsel reposunda son 7 günün klasörleri tutulur, eskiler her paylaşımda silinir.

## Para kazanma (affiliate) ve #reklam

Şu an linkler düz ürün linki. Trendyol / Hepsiburada / Amazon TR satış ortaklığı onayı
gelince link biçimini söyle, `telegram_caption`'a eklenir.
Affiliate linkleri kullanmaya başladığın gün `DEALS_HASHTAGS`'e `#reklam` ekle
(Ticaret Bakanlığı sosyal medya reklam kuralları).

## Zamanlanmış görevleri yeniden kurmak

```
powershell -ExecutionPolicy Bypass -File scripts\install_deal_tasks.ps1
```

## Sorun giderme

- Log: `logs/scraper.log` (Instagram/Telegram anahtarları loglarda gizlenir).
- "yalnızca N fırsat bulundu": gece taraması çalışmamış ya da indirimli ürün az.
  `run_stats` tablosuna ya da logda `pipeline` satırlarına bak.
- "Instagram paylaşımı başarısız: Invalid OAuth access token": anahtar iptal olmuş ya da
  (IGAA… ise) süresi dolmuş; panelde **Generate token** ile yenisini al, `.env`'ye yaz.
- Bilgisayar 10:00 / 14:00 / 19:00'da kapalıysa o paylaşım atlanır (bilerek; açılınca
  üst üste gönderi düşmesin diye).
