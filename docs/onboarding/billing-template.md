# Fatura E-posta Şablonları

## İlk Fatura (30. gün)

**Kime:** `{müşteri_email}`
**CC:** `{muhasebe_email}`
**Konu:** Metrio — {ay_adı} Dönemi Faturası

---

Merhaba `{iletişim_kişisi}`,

**{şirket_adı}** için `{dönem_başlangıç}` — `{dönem_bitiş}` dönemine ait hizmet
faturası ektedir.

| Kalem | Tutar |
|-------|-------|
| Metrio Fiyat Takip — {paket_adı} | {tutar_kdv_hariç} TL |
| KDV (%20) | {kdv} TL |
| **TOPLAM** | **{toplam} TL** |

**Ödeme bilgileri:**

- Banka: `{banka_adı}`
- IBAN: `TR__ ____ ____ ____ ____ ____ __`
- Hesap sahibi: `{senin_şirket_ünvanı}`
- Açıklama: `Metrio-{slug}-{ay}`

**Fatura numarası:** `{e-arşiv_fatura_no}`
**Fatura tarihi:** `{fatura_tarihi}`
**Son ödeme tarihi:** `{son_ödeme}` _(fatura tarihinden 14 gün sonra)_

Fatura PDF'i ekte ve e-arşiv sisteminden de (`e-arsiv.gib.gov.tr`) indirebilirsiniz.

Herhangi bir sorunuz varsa `muhasebe@metrio.app` adresine yazabilirsiniz.

Teşekkürler,
**Metrio Muhasebe**

---

## Yenileme Hatırlatması (25. gün — fatura kesilmeden 5 gün önce)

**Konu:** Metrio — Aboneliğiniz 5 Gün Sonra Yenileniyor

---

Merhaba `{iletişim_kişisi}`,

Hatırlatma: Metrio aboneliğiniz `{yenileme_tarihi}` tarihinde otomatik olarak
yenilenecek. Yeni dönemin faturası aynı gün `{müşteri_email}` adresine gönderilecek.

Bu ay için hizmetinizde:
- `{toplam_tarama}` başarılı tarama yapıldı
- `{toplam_alarm}` fiyat alarmı iletildi
- `{toplam_rapor}` haftalık rapor gönderildi

Sistem memnuniyetinizi duymak isteriz. Değişiklik / iptal talebiniz varsa lütfen
yenileme tarihinden önce bize bildirin.

**Metrio Ekibi**

---

## E-Arşiv Uyumluluk Notları

- Faturada **"e-Arşiv Fatura"** ibaresi bulunmalı (otomatik, Paraşüt/Logo/Mikro'dan kesildiğinde)
- Fatura numarası formatı: `MTR2026000000001` (3 harf + yıl + 9 hane seri)
- E-arşiv portala 7 gün içinde rapor edilmeli (otomatik)
- KDV oranı: standart hizmet %20 (2024 sonrası)
- İhracat / yurtdışı müşteri varsa KDV'siz, "yurtdışı hizmet ihracı" notu eklenmeli
- KVKK: fatura bilgilerinde yalnızca sözleşmede onay verilen e-postalar kullanılmalı
- GİB e-arşiv zorunluluğu: yıllık 5M TL ciro üstü. Altında isteğe bağlı ama önerilir.

### Aracı Yazılım Önerileri

- **Paraşüt** — KOBİ için, entegrasyonu kolay
- **Logo İşbaşı** — Orta ölçek
- **Mikro** — Muhasebeci tercih ediyorsa

Şablonlar Paraşüt'te "Metrio — Aylık Abonelik" adıyla kayıtlı.
