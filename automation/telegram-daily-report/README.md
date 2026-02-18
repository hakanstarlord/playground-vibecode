# Daily Telegram Report Automation

Bu otomasyon her sabah saat **08:00 (Türkiye saati)** Telegram üzerinden şu bilgileri gönderir:

- O günün hava durumu
- Altın ve gümüş fiyatı (XAU/USD, XAG/USD)
- Bitcoin ve Ethereum fiyatı (BTC/USD, ETH/USD)
- Günün favori maçları

## Veri kaynakları

- Hava durumu: Open-Meteo
- Piyasa verisi: Stooq
- Maç verisi: ESPN scoreboard API

## Kurulum

1. Telegram'da bir bot oluştur (`@BotFather`) ve bot token'ını al.
2. Mesaj göndermek istediğin `chat_id` bilgisini öğren.
3. GitHub deposunda **Settings > Secrets and variables > Actions** bölümüne şu secret'ları ekle:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - (Opsiyonel) `CITY`
   - (Opsiyonel) `LAT`
   - (Opsiyonel) `LON`

> `CITY`, `LAT`, `LON` verilmezse varsayılan olarak İstanbul kullanılır.

## Çalışma zamanlaması

Workflow dosyası: `.github/workflows/daily-telegram-report.yml`

- `cron: "0 5 * * *"` => UTC 05:00 = Türkiye saati 08:00
- İstersen `workflow_dispatch` ile manuel de tetikleyebilirsin.

## Lokal test

```bash
cd automation/telegram-daily-report
TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy node index.js
```

## Notlar

- GitHub Actions cron UTC çalışır.
- Maçlar favori takım eşleşmesine göre önceliklendirilir, sonra saatine göre sıralanır.
