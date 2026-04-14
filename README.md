# Fiyat Radarı

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
