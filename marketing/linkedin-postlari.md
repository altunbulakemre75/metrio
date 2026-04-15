# LinkedIn Post Taslakları

Hedef: E-ticaretçilere, marka yöneticilerine ulaşmak. Post'lar hikâye anlatır, problem-çözüm paralel olur.

---

## Post 1 — Lansman / problem odaklı

> Bir dönem her sabah rutinim şöyleydi:
>
> 1. Kahveyi koy ☕
> 2. Rakiplerimizin Trendyol sayfasını aç
> 3. 50 ürünün fiyatına bak, Excel'e yaz
> 4. Dünden farklılaşanları işaretle
> 5. Şefe gönder
>
> 45 dakika. Her gün.
>
> Bir sabah gözüm açılmadan "bu iş otomatize olur" dedim ve kolları sıvadım.
>
> Şimdi Metrio adında bir sistem var:
> — Her gece rakipleri tarıyor
> — %20+ fiyat hareketini yakaladığında Telegram'a alarm atıyor
> — Haftalık PDF raporu Pazartesi sabah mail kutusunda
>
> E-ticarette rakip fiyat takibini manuel yapan arkadaşlar, lütfen bana mesaj atın. Bu dertten kurtulmanın zamanı geldi.
>
> #eticaret #trendyol #otomasyon #fiyatTakibi

**Neden çalışır:** İlk satır hikaye kancası, numaralı liste okumayı kolaylaştırır, sonu net CTA.

---

## Post 2 — Teknik / Yapı odaklı

> "Fiyat takibini nasıl otomatize ediyorsunuz?" sorusunun teknik cevabı:
>
> 🕷 **Scraping** — Playwright ile Chromium headless, gerçek tarayıcı davranışı. BeautifulSoup yerine Playwright çünkü Trendyol JS-heavy, kart yüklenmesini beklemek şart.
>
> 💾 **Depolama** — SQLite, iki tablolu zaman serisi şeması: `products` (stabil kimlik) + `price_snapshots` (her çekim bir satır). İndexler ürün_id + tarih üzerinde.
>
> 🚨 **Anomali tespiti** — Son 30 günün ortalamasından %20+ sapma. Güven skoru snapshot sayısına bağlı (5-15-30+).
>
> 🤖 **Bildirim** — Telegram Bot API (günlük özet + bireysel alarm), SMTP + PDF ek (haftalık rapor).
>
> 📊 **Dashboard** — Streamlit + Plotly, 5 sayfa (özet, fırsatlar, anomaliler, trendler, ürün detay).
>
> Tüm kod TDD ile yazıldı, 106 test geçiyor. Hafta sonu ekleyeceğim — Hepsiburada scraper'ı ve Claude API destekli yorum katmanı.
>
> Benzer bir sistem kurmak isteyenlere GitHub'dan mimari özetini paylaşırım.
>
> #python #webscraping #sqlite #streamlit #tdd

**Neden çalışır:** Teknik derinlik sinyal verir, mühendis kitlesi yeniden paylaşır, "106 test" güven verir.

---

## Post 3 — Sosyal kanıt / vaka odaklı

> Geçen hafta bir kozmetik markası için demo yaptım.
>
> 10 dakika dashboard'u gösterdim. 11. dakikada şu soruyu sordu:
>
> "{X markası} geçen hafta 7 üründe indirime gitmiş. Biz bunun 4'ünü görmedik, cuma siparişlerimiz %18 düştü. Bu sistem o 4'ü yakalar mıydı?"
>
> Ekran paylaştım, filtreyi açtım — sistem 7'sini de yakalamış, Telegram alarmı atmıştı. Sadece onlara kurulu değildi. Yani olsaydı, yakalayacaktı.
>
> O soru kararı verdirdi. Bu hafta kurulum var.
>
> **Ders:** Demo'da özellikleri saymak değil, müşterinin geçmiş ağrısını veriyle yüzleştirmek satar.
>
> E-ticarette buna benzer dertleri olan markalar varsa, DM açık.
>
> #eticaret #satış #urunYonetimi #trendyol

**Neden çalışır:** Hikâye formatı, spesifik rakam (%18), sonda ders + CTA.

---

## Post takvimi önerisi

| Hafta | Post | Saat |
|-------|------|------|
| 1 | Post 1 (lansman) | Salı 09:00 |
| 2 | Post 2 (teknik) | Çarşamba 10:00 |
| 3 | Post 3 (vaka) | Salı 09:00 |

**Salı/Çarşamba sabah** LinkedIn'de B2B engagement en yüksek. Pazartesi ve Cuma zayıf.

## Genel kurallar

1. **İlk 2 satır kritik.** Kullanıcı "daha fazlasını gör"a basacak mı buraya bakar.
2. **Numaralı liste veya emoji ile parçala.** Metin bloku geçilir.
3. **Hashtag 3-5 tane.** Fazlası spam algılanır.
4. **Comment'lere 24 saat içinde yanıt ver.** LinkedIn algoritması engagement takip eder.
5. **Haftada 1-2 post yeterli.** Kalite > miktar.
