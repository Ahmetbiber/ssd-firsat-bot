# SSD Fırsat Takip Botu

DonanımArşivi **Sıcak Fırsatlar** forumunu 15 saniyede bir kontrol eder. Yeni bir **SSD** konusu
açılınca telefona başlık + link ile bildirim gönderir. Laptop, hazır sistem, kasa, mini PC,
anakart, GPU/CPU/RAM paketleri ve SSD kutuları filtrelenir (yanlış alarm yok).

GitHub Actions üzerinde çalışır; bilgisayarın açık olmasına gerek yoktur.

## Kurulum

Bildirim için **birini** seç (ikisi birden de olur):

### A) ntfy (en kolayı, hesap gerekmez)
1. Telefona **ntfy** uygulamasını kur (Play Store / App Store).
2. Uygulamada **+** → tahmin edilemeyecek bir konu adı yaz, ör. `ssd-firsat-k7x93qm2`.
3. Repo → **Settings → Secrets and variables → Actions → New repository secret**
   - `NTFY_TOPIC` = aynı konu adı

### B) Telegram
1. Telegram'da **@BotFather** → `/newbot` → verilen **token**'ı kopyala.
2. Yeni botuna bir mesaj at, sonra tarayıcıda aç:
   `https://api.telegram.org/bot<TOKEN>/getUpdates` → `"chat":{"id": ...}` sayısını kopyala.
3. Repo secrets:
   - `TELEGRAM_BOT_TOKEN` = token
   - `TELEGRAM_CHAT_ID` = chat id

### Başlat
1. **Actions** sekmesi → workflow'ları etkinleştir.
2. **SSD firsat takip → Run workflow** → "Sadece test bildirimi gönder" işaretle → telefona test gelmeli.
3. Bir kez de işaretsiz **Run workflow** de. Sonrası otomatik (her 15 dk zamanlayıcı yedeği var).

## Notlar
- Repo **public** olmalı: Actions dakikası public repolarda sınırsız, private'ta ayda 2000 dk ile yetmez.
  Secret'lar public repoda da gizli kalır.
- Bot `state/seen.json` dosyasını kendisi commit'ler (hangi konuları gördüğünü hatırlamak için).
- Forum ~5 dk okunamazsa uyarı bildirimi gelir.
- Filtreyi denemek: `python3 bot.py test "Samsung 990 Pro 2TB 9.999 TL"`
