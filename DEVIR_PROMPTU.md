Bu Windows bilgisayara bir SSD fırsat takip botu kurmanı istiyorum. Ben teknik değilim; her şeyi sen kur, bana sadece gerektiğinde basit sorular sor. Benimle Türkçe konuş.

## Bot ne yapıyor
GitHub reposu (public): https://github.com/Ahmetbiber/ssd-firsat-bot — `bot.py` DonanımArşivi forumunu (Sıcak Fırsatlar 15 sn, tüm forum 1 dk), `telegram_kanallari.txt` içindeki Telegram kanallarını (1 dk) ve isteğe bağlı olarak `instagram.py` ile Instagram hikayelerini (~5 dk, OCR ile) izliyor. Yeni bir SSD fırsatı görünce ntfy ile telefonuma ve Windows bildirimi olarak bilgisayara haber veriyor. Kod daha önce bulutta test edildi ve çalışıyor; filtre mantığını değiştirme, sadece kurulumu yap ve Windows'a özgü bir sorun çıkarsa düzelt. README.md'de Windows ve Instagram adımları var, önce onu oku.

## Yapılacaklar (sırayla)
1. **Python**: `python --version` ile kontrol et. Yoksa `winget install -e --id Python.Python.3.12` ile kur (PATH'e eklensin), yeni terminalde tekrar kontrol et.
2. **Repoyu indir**: `%USERPROFILE%\Documents\ssd-firsat-bot` klasörüne (git varsa `git clone`, yoksa ZIP indirip çıkar).
3. **Paketler**: `python -m pip install --upgrade instaloader pytesseract pillow`
4. **Tesseract OCR**: `winget install -e --id UB-Mannheim.TesseractOCR`. Türkçe dil dosyasını ekle: https://github.com/tesseract-ocr/tessdata_fast/raw/main/tur.traineddata dosyasını `C:\Program Files\Tesseract-OCR\tessdata\` içine koy (yönetici izni gerekebilir). `"C:\Program Files\Tesseract-OCR\tesseract.exe" --list-langs` çıktısında `tur` görünmeli.
5. **ntfy ayarı**: Klasörde `ntfy.txt` oluştur, içinde tek satır, boşluksuz: `<NTFY_KONU>`
6. **Bildirim testi**: Klasörde `set NTFY_TOPIC=<NTFY_KONU>` ile `python bot.py ping` çalıştır. Bana sor: hem bilgisayarda (sağ altta Windows bildirimi) hem telefonda bildirim geldi mi? Windows bildirimi gelmezse `bot.py` içindeki `windows_toast` fonksiyonunu düzelt (PowerShell ile WinRT toast; ntfy kısmı çalışıyor, ona dokunma). ntfy bazen ilk denemede 429 verir, bot tekrar dener; bu normal.
7. **Instagram (isteğe bağlı)**: Bana hangi Instagram hesaplarının hikayelerini takip etmek istediğimi sor ve `instagram_hesaplari.txt` dosyasına her satıra bir hesap yaz. Sonra girişi BENİM yapmam lazım: `start "" instagram_giris.bat` ile ayrı bir pencere aç ve bana o pencereye kullanıcı adımı ve şifremi yazmamı söyle. **Şifremi asla sohbette isteme, görme, bir yere yazma.** Giriş bitince `instagram_kullanici.txt` oluşmuş olmalı. Instagram "şüpheli giriş" derse telefondan onaylamamı söyle ve tekrar denet.
8. **Kısa doğrulama**: Klasörde `set NO_GIT=1`, `set NTFY_TOPIC=<NTFY_KONU>`, `set RUN_SECONDS=150`, `set PYTHONIOENCODING=utf-8` ile `python bot.py` çalıştır ve çıktıyı incele: `basladi`, `atlandi|...` satırları, `telegram: ... eklendi` satırları ve (Instagram kurulduysa) `instagram takibi acik` görünmeli; `okuma hatasi`, `instagram hatasi` veya Traceback varsa düzelt.
9. **Sürekli çalışsın**: `baslat.bat` için Başlangıç klasörüne (`shell:startup`) bir kısayol oluştur (PowerShell `WScript.Shell` ile), pencere simge durumunda açılsın. Sonra `baslat.bat`'ı şimdi de başlat. Pencere açık kaldıkça bot çalışır; bilgisayar açılınca kendiliğinden başlar.
10. **Bitiş**: Bana kısa bir özet ver (ne kuruldu, test sonuçları, varsa sorunlar). Sonra bana şunu söyle: "Eski bulut oturumuna dönüp 'çalışıyor' yaz; oradaki bulut botu ve 2 zamanlanmış kontrol görevi kapatılsın, yoksa her fırsat için iki bildirim gelir."

## Notlar
- `<NTFY_KONU>`: kullanıcının ntfy konu adı. Bana yapıştırılan promptta yazıyorsa onu kullan, yoksa kullanıcıya sor (telefonundaki ntfy uygulamasında abone olduğu konu).
- Forum (Cloudflare) GitHub Actions makinelerini engelliyor; bu yüzden bot ev internetinde, bu bilgisayarda çalışmalı. Workflow'u açma.
- Botun durumu `state\seen.json` içinde; ilk çalıştırmada mevcut konular/mesajlar bildirilmez, bu normal.
- Kişisel bilgilerimi (şifre, Instagram oturumu) hiçbir dış servise ya da GitHub'a gönderme; `instagram_kullanici.txt` ve `state\` zaten `.gitignore`'da.
