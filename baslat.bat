@echo off
chcp 65001 >nul
title SSD Firsat Takip
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set NO_GIT=1

rem --- ntfy konu adi: ilk calistirmada sorulur ve ntfy.txt dosyasina kaydedilir ---
if not exist ntfy.txt (
  set /p KONU=ntfy konu adini yaz ^(ornek: ssd-firsat-xxxx^): 
  call echo %%KONU%%> ntfy.txt
)
set /p NTFY_TOPIC=<ntfy.txt

rem --- Python var mi? ---
where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo HATA: Python bulunamadi. python.org adresinden kur, kurarken
  echo "Add python.exe to PATH" kutusunu isaretle. Sonra bu dosyayi tekrar calistir.
  pause
  exit /b
)

echo Test bildirimi gonderiliyor (bilgisayar + telefon)...
python bot.py ping
echo SSD takip basladi. Bu pencereyi kapatma (kucultebilirsin).
:dongu
python bot.py
echo Bot durdu, 30 saniye sonra yeniden baslatiliyor...
timeout /t 30 /nobreak >nul
goto dongu
