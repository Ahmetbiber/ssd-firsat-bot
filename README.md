# SSD Fırsat Takip Botu

DonanımArşivi'nde yeni bir **SSD** fırsatı görülünce telefona başlık + link ile bildirim gönderir.

- **Sıcak Fırsatlar**: 15 saniyede bir yeni konular
- **Tüm forum** ("Yeni mesajlar", dakikada bir): diğer bölümlerde açılan yeni konular
  (başlıkta fiyat olmalı, soru konusu olmamalı) ve fırsat/alışveriş konularına yazılan
  yeni cevaplar (aynı satırda SSD + fiyat; alıntı ve imzalar hariç)

Laptop, hazır sistem, kasa, mini PC, anakart, GPU/CPU/RAM paketleri ve SSD kutuları filtrelenir.

> **Not:** Forum Cloudflare ile GitHub Actions makinelerini engelliyor (HTTP 403), bu yüzden
> workflow'un otomatik başlatması kapalı. Botu ev internetine bağlı bir cihazda çalıştır:
> `NO_GIT=1 NTFY_TOPIC=<konu-adin> python3 bot.py`

## Windows bilgisayarda çalıştırma (önerilen)

1. **Python kur:** [python.org/downloads](https://www.python.org/downloads/) → kurulumun ilk ekranında
   **"Add python.exe to PATH"** kutusunu işaretle.
2. **Botu indir:** Bu sayfada yeşil **Code** → **Download ZIP** → ZIP'i bir klasöre çıkar
   (ör. `Belgeler\ssd-firsat-bot`).
3. **Çalıştır:** Klasördeki **`baslat.bat`** dosyasına çift tıkla. İlk seferde ntfy konu adını sorar,
   yaz ve Enter'a bas. Siyah pencere açık kaldığı sürece takip çalışır (küçültebilirsin).
4. **Bilgisayar açılınca otomatik başlasın:** `baslat.bat`'a sağ tık → **Kısayol oluştur**.
   `Win + R` → `shell:startup` yaz → Enter. Açılan klasöre kısayolu taşı.

Bot çökerse pencere 30 saniye sonra kendini yeniden başlatır. İlk çalıştırmada mevcut konular
bildirilmez, sadece bundan sonra açılanlar bildirilir.

## GitHub Actions ile kurulum (şu an forum engellediği için çalışmıyor)

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
