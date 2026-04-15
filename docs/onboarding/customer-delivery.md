# Müşteri Teslim E-postası + Kullanım Rehberi

---

## Teslim E-postası Şablonu

**Kime:** `{müşteri_email}`
**Konu:** Metrio — Fiyat Takibiniz Artık Aktif

---

Merhaba `{iletişim_kişisi}`,

**{şirket_adı}** için Metrio fiyat takip sisteminiz başarıyla kuruldu. Artık her gece
03:00'te rakip fiyatlarınız otomatik taranıyor ve anlamlı değişimler için Telegram'dan
anında haber alacaksınız.

**Sistem detayları:**

- **Takip edilen platformlar:** `{platforms}`
- **Takip edilen rakipler:** `{rakip_sayısı}` rakip
- **Fiyat alarm eşiği:** `%{eşik}`
- **Dashboard:** `{dashboard_url}` (VPN/giriş bilgileriniz ayrı e-postayla)
- **Telegram botu:** [@MetrioFiyatBot](https://t.me/MetrioFiyatBot)

**Bu hafta beklentiniz:**

- Her sabah 08:00 civarı Telegram'a gece taramasının özeti düşer
- Pazartesi sabah haftalık özet e-postası alırsınız (ilki önümüzdeki pazartesi)
- Fiyat %{eşik} üzeri hareket ederse anında Telegram alarmı

**Destek kanalı:**

- WhatsApp: `{senin_whatsapp}`
- E-posta: `support@metrio.app`
- Yanıt süremiz: mesai saatlerinde 2 saat, hafta sonu 1 gün

İyi takipler,
**Metrio Ekibi**

---

## Kullanım Rehberi (müşteriye ek PDF / dokuman)

### 1. Telegram Bot Komutları

Bota `/start` demenizi zaten rica ettik. Kullanabileceğiniz komutlar:

| Komut | Ne yapar |
|-------|----------|
| `/durum` | Son çalışma ne zaman, başarılı mı? |
| `/rapor` | Bu haftanın özet raporunu gönder |
| `/fiyat {ürün}` | Belirli bir üründe son fiyat trendi |
| `/alarmlar` | Aktif fiyat alarmlarını listele |
| `/yardım` | Tüm komutlar |

### 2. Dashboard Ne Gösterir

Dashboard URL'inizde 3 ana sayfa var:

- **Genel bakış:** Bugün vs dün fiyat değişimi özeti
- **Rakip detay:** Her rakip için ürün listesi + 30 günlük grafik
- **Alarmlar:** Son 7 gündeki tüm fiyat uyarıları

### 3. Haftalık Rapor (E-posta)

Her pazartesi 09:00'da otomatik gelir. İçerik:

- Geçen haftanın en büyük 5 fiyat düşüşü
- Yeni stoklara giren ürünler
- Kaybolan ürünler (stok tükenmiş veya listeden düşmüş)
- Sizin markanızla ilgili fiyat pozisyonu

### 4. Yeni Rakip Eklemek / Çıkarmak

WhatsApp'tan bize yazın, aynı gün içinde ekleriz. Otomatik self-serve arayüzü
gelecek ay planında.

### 5. SSS

**S: Bir gün tarama çalışmadı, ne olur?**
C: Sistem ertesi gün otomatik devam eder. Biz ayrıca izliyoruz, 24 saat üst üste
hata olursa biz sizi ararız.

**S: Verilerim güvende mi?**
C: Tüm veriler bizim sunucumuzda lokalde. 3. parti ile paylaşılmaz. KVKK uyumluyuz.

**S: Aboneliği iptal istersem?**
C: 30 gün önceden yazılı bildirim. Son ayın ücreti tahsil edilir, veriler
müşteriye export edilir ve silinir.
