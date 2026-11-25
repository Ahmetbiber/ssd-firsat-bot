#!/usr/bin/env python3
"""Instagram hikaye takibi (istege bagli, SADECE kendi bilgisayarinda).

Kurulum (bir kere):
  1) instagram_giris.bat  -> Instagram'a kendi hesabinla giris yapar, oturumu bilgisayara kaydeder
  2) instagram_hesaplari.txt -> takip edilecek hesaplar (her satira bir hesap)
  3) Tesseract OCR (hikayedeki yaziyi okumak icin) - README'ye bak

Hesabini korumak icin: hikayeler IG_EVERY saniyede bir (varsayilan 300 = 5 dk, rastgele +/- 60 sn),
tum hesaplar tek istekte kontrol edilir. Instagram "yavasla" derse bot 30 dk bekler.
"""
import io, os, random, re, time, urllib.request

DIR = os.path.dirname(os.path.abspath(__file__))
ACC_FILE = os.path.join(DIR, "instagram_hesaplari.txt")
USER_FILE = os.path.join(DIR, "instagram_kullanici.txt")
IG_EVERY = int(os.environ.get("IG_EVERY", "300"))
TESSERACT_WIN = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def read_list(path):
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return []
    out = []
    for l in lines:
        l = l.split("#")[0].strip()
        m = re.search(r"(?:instagram\.com/(?:stories/)?|@)?([A-Za-z0-9_.]{2,30})/?(?:\?.*)?$", l)
        if l and m:
            out.append(m.group(1).lower())
    return out


def configured():
    return bool(read_list(ACC_FILE)) and bool(read_list(USER_FILE))


# ---------------------------------------------------------------- OCR
_lang = None

def ocr(img_bytes):
    """Hikaye gorselindeki yaziyi okur. Acik ve koyu zemin icin iki kez dener."""
    global _lang
    import pytesseract
    from PIL import Image, ImageOps
    if os.name == "nt" and os.path.exists(TESSERACT_WIN):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_WIN
    if _lang is None:
        try:
            langs = pytesseract.get_languages(config="")
            _lang = "tur+eng" if "tur" in langs else "eng"
        except Exception:
            _lang = "eng"
    img = Image.open(io.BytesIO(img_bytes)).convert("L")
    if img.width < 1000:
        img = img.resize((img.width * 2, img.height * 2))
    img = ImageOps.autocontrast(img)
    texts = []
    for im in (img, ImageOps.invert(img)):
        try:
            texts.append(pytesseract.image_to_string(im, lang=_lang, config="--psm 11"))
        except Exception as e:
            texts.append("")
            print("ocr hatasi:", e, flush=True)
    return "\n".join(texts)


def story_hit(text, is_ssd, norm, POS):
    """Tum hikaye metni SSD ise (laptop/sistem vb. degilse) en anlamli satiri dondurur."""
    flat = re.sub(r"\s+", " ", text)
    if not is_ssd(flat):
        return None
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    for l in lines:
        if l and POS.search(norm(l)):
            return l
    return flat[:150]


# ---------------------------------------------------------------- izleyici
class IGWatcher:
    def __init__(self, state):
        state.setdefault("ig", {})
        self.st = state["ig"]
        self.st.setdefault("seen", [])
        self.st.setdefault("uid", {})
        self.st.setdefault("accounts", [])
        self.seen = set(self.st["seen"])
        self.L = None
        self.next_at = 0
        self.login_alerted = False

    def due(self):
        return time.time() >= self.next_at

    def _login(self):
        import instaloader
        user = read_list(USER_FILE)[0]
        L = instaloader.Instaloader(quiet=True, download_pictures=False, download_videos=False,
                                    download_video_thumbnails=False, save_metadata=False,
                                    max_connection_attempts=1)
        L.load_session_from_file(user)
        self.L = L

    def check(self, notify, is_ssd, norm, POS, log):
        import instaloader
        self.next_at = time.time() + IG_EVERY + random.randint(-60, 60)
        try:
            if self.L is None:
                self._login()
            names = read_list(ACC_FILE)
            for n in names:
                if n not in self.st["uid"]:
                    self.st["uid"][n] = instaloader.Profile.from_username(self.L.context, n).userid
                    time.sleep(random.uniform(2, 5))
            new_accounts = set(names) - set(self.st["accounts"])
            ids = [self.st["uid"][n] for n in names]
            count = 0
            for story in self.L.get_stories(userids=ids):
                for item in story.get_items():
                    mid = str(item.mediaid)
                    if mid in self.seen:
                        continue
                    self.seen.add(mid)
                    owner = (item.owner_username or "").lower()
                    link = "https://www.instagram.com/stories/%s/%s/" % (owner, mid)
                    if owner in new_accounts:
                        continue                    # yeni eklenen hesabin mevcut hikayeleri bildirilmez
                    count += 1
                    img = urllib.request.urlopen(item.url, timeout=60).read()
                    hit = story_hit(ocr(img), is_ssd, norm, POS)
                    log("%s %s|Instagram %s|%s|%s" % (time.strftime("%H:%M:%S"), "SSD" if hit else "atlandi",
                                                      owner, (hit or "")[:100], link))
                    if hit:
                        notify(hit[:150] + " [Instagram: %s hikaye]" % owner, link)
            self.st["accounts"] = names
            self.st["seen"] = sorted(self.seen)[-1000:]
            self.login_alerted = False
            if count:
                log("%s instagram: %d yeni hikaye kontrol edildi" % (time.strftime("%H:%M:%S"), count))
            return True
        except Exception as e:
            name = type(e).__name__
            log("%s instagram hatasi: %s %s" % (time.strftime("%H:%M:%S"), name, str(e)[:150]))
            if "Login" in name or "login" in str(e) or "BadCredentials" in name or "session" in str(e).lower():
                self.L = None
                self.next_at = time.time() + 1800
                if not self.login_alerted:
                    notify("Instagram oturumu gecersiz. instagram_giris.bat'i tekrar calistir.", "", head="SSD takip")
                    self.login_alerted = True
            elif "429" in str(e) or "wait a few minutes" in str(e) or "TooManyRequests" in name:
                self.next_at = time.time() + 1800   # Instagram "yavasla" dedi: 30 dk bekle
            return False
