# Intranet Projesi

Tam yigin (full stack) intranet uygulamasi; FastAPI tabanli bir arka uc (`intranet-backend`), React + Vite tabanli bir on uc (`intranet-frontend`) ve plaka tanima icin yardimci betikler (`entegre`) icerir.

## Dizin yapisi

- `intranet-backend/` &mdash; FastAPI uygulamasi, veri tabani ve plaka/RAG servisleri
- `intranet-frontend/` &mdash; React/Vite istemcisi
- `entegre/` &mdash; Plaka tanima ve OCR icin bagimsiz betikler

## Gereksinimler

- Python 3.10+ ve `pip`
- Node.js 18+ ve `npm`
- macOS icin Xcode Command Line Tools (veya Linux icin build-essential) tavsiye edilir

## Arka uc (FastAPI)

```bash
cd intranet-backend
python3 -m venv venv
source venv/bin/activate           # Windows icin: venv\Scripts\activate
pip install -r requirements.txt
```

### Veri tabani

Proje gelistirme veri tabanini SQLite ile tutar.

```bash
# Veri tabanini sifirla
rm -f src/database/app.db

# Test verileri olustur
python3 create_test_data.py
```

### Uygulamayi calistirma

```bash
cd intranet_backend
```
```bash
python3 src/main.py
```

Calisan servis varsayilan olarak `http://127.0.0.1:8000` adresinden erisilebilir.

### Ortam degiskenleri

Gerekli gizli degerler icin `intranet-backend/.env` dosyasi kullanilir. `example` dosyasi yoksa, ihtiyaca gore yenisini olusturabilirsiniz. Dosya `.gitignore` kapsaminda oldugundan repoya dahil edilmez.

## On uc (React + Vite)

```bash
cd intranet-frontend
npm install
npm run dev -- --host
```

`--host` bayragi, Vite'in ag uzerinden erisilebilir olmasini saglar. Tarayicidan `http://localhost:5173` adresine gidin.

### Vite CLI hatasi

`{ "error": "server_error: Unknown argument: show_log", "success": false }` hatasini aliyorsaniz:

1. `npm install` komutunun hatasiz tamamlandigini dogrulayin.
2. `npm run dev -- --host` komutunu Vite 5 ve uzeri ile calistirdiginizdan emin olun.
3. Sorun devam ederse `package-lock.json` ve `node_modules/` klasorunu silip yeniden `npm install` calistirin.

## Plaka/OCR betikleri

`entegre/` klasoru, tek basina calistirilabilen plaka ve OCR modellerini barindirir:

```bash
cd entegre
pip install -r requirements.txt
python3 main.py
```

Bu betikler, arka ucteki FastAPI servisleri ile paylasilan modelleri ve is akisini test etmeye yarar.

## Gelistirme ipuclari

- Kod standartlarini korumak icin `ruff`, `black` ve `pytest` gibi araclar kurulum asamasinda otomatik eklenir; gerekirse manuel calistirin.
- Git gecmisini temiz tutmak icin buyuk dosyalari (`*.pt`, `*.sqlite3`, gecici depolama) repoya eklemeyin; `.gitignore` bunlari kapsar.

## Lisans

Proje acik lisansi henuz belirtilmedi. Kurumsal kullanim sartlarini belirlemek icin proje sahibine basvurun.
