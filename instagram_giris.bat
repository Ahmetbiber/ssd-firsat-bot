@echo off
chcp 65001 >nul
title Instagram giris
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo Gerekli paketler kuruluyor (bir kere)...
python -m pip install --quiet --upgrade instaloader pytesseract pillow
if errorlevel 1 ( echo HATA: paketler kurulamadi. Python kurulu mu? & pause & exit /b )
echo.
set /p IGUSER=Instagram kullanici adin (@ olmadan): 
echo.
echo Simdi sifren sorulacak. Yazarken ekranda GORUNMEZ, bu normal. Yaz ve Enter'a bas.
echo Iki adimli dogrulama aciksa telefonuna gelen kod da sorulur.
echo Sifren sadece bu bilgisayarda Instagram'a gonderilir, hicbir yere kaydedilmez.
echo.
python -m instaloader --login %IGUSER%
if errorlevel 1 (
  echo.
  echo Giris basarisiz. Instagram "supheli giris" dediyse telefondan onaylayip tekrar dene.
  pause
  exit /b
)
echo %IGUSER%> instagram_kullanici.txt
echo.
echo Giris tamam, oturum kaydedildi.
echo Simdi instagram_hesaplari.txt dosyasina takip edilecek hesaplari yaz, sonra baslat.bat'i yeniden ac.
pause
