#!/usr/bin/env python3
"""DonanimArsivi Sicak Firsatlar -> yeni SSD konusu acilinca telefona bildirim.

Ortam degiskenleri (GitHub Secrets):
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID   -> Telegram bildirimi
  NTFY_TOPIC                              -> ntfy.sh bildirimi
  (ikisi de verilebilir; hicbiri yoksa sadece ekrana yazar)
  RUN_SECONDS  kac saniye calissin (varsayilan 20400 = 5sa 40dk)
  INTERVAL     kac saniyede bir kontrol (varsayilan 15)
  NO_GIT=1     durum dosyasini commit'leme (yerel test icin)

Kullanim:
  python3 bot.py                 izlemeyi baslat
  python3 bot.py test "baslik"   filtreyi dene
  python3 bot.py ping            test bildirimi gonder
"""
import html, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

BASE = "https://forum.donanimarsivi.com"
URL = BASE + "/forumlar/Sicakfirsatlar/?order=post_date&direction=desc"
DIR = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(DIR, "state", "seen.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "20400"))
INTERVAL = int(os.environ.get("INTERVAL", "15"))
SAVE_EVERY = 600

# ---------------------------------------------------------------- filtre
TR = str.maketrans("çşğüöı", "csguoi")
# Magaza adlari ("Vatan PC", "Vatan Bilgisayar") urunle karismasin
STORES = re.compile(r"\b(vatan|sinerji|tek|gaming ?gen|inceh?esap|ebrar)\s?(pc|bilgisayar)\w*")

def norm(t):
    t = t.replace("İ", "i").replace("I", "i").lower().translate(TR)
    return STORES.sub(" magaza ", t)

# SSD oldugunu gosteren seyler
POS = re.compile(r"\bssd\b|\bnvme\b|\bnmve\b|\bnvm\b|"
    r"990 ?(pro|evo)|980 ?pro|samsung 980|970 ?evo|870 ?(evo|qvo)|9100 ?pro|samsung t[579]\b|"
    r"\bsn(5000|580|570|770|850x?|8100|7100)\b|wd ?black|wd_black|"
    r"predator gm\d|\bxs[12]000\b|extreme (pro )?portable|crucial x(6|8|9|10)\b|"
    r"\bnv[123]\b|kc3000|fury renegade|\ba400\b|"
    r"crucial (p3|p5|t500|t700|t705|mx500|bx500)|\b(t500|t700|t705|mx500|bx500)\b|"
    r"exceria|\bnm\d{3,4}\b|lexar|legend \d{3}|gammix|spatium|\bmp(600|700|44|33)\b|"
    r"hiksemi|solidigm|firecuda|sabrent|kingspec|netac|cardea|"
    r"(m\.?2|pcie|gen ?[345]).{0,60}\b\d+ ?(tb|gb)\b|\b\d+ ?(tb|gb)\b.{0,60}(m\.?2|pcie|gen ?[345])")

# Hazir sistem / laptop / anakart / aksesuar -> yanlis alarm olmasin
NEG = re.compile(r"laptop|notebook|diz[uü]st[uü]|masa[uü]st[uü]|bilgisayar|hazir sistem|"
    r"oyun sistemi|\bsistem\b|\bkasa\b|\bpc\b|mini ?pc|macbook|monoblok|all.?in.?one|"
    r"anakart|motherboard|\b(a[56]20|b[4-8][56]0|x[5-8]70e?|h[5-8]10|z[6-8]90)[a-z]?\b|"
    r"telefon|tablet|\bps5\b|konsol|steam deck|"
    r"\brtx\b|\bgtx\b|\brx ?\d{3,4}|ekran karti|i[3579][ -]\d|ryzen|core ultra|i[sş]lemci|"
    r"\bram\b|\bddr[345]\b|"
    r"vivobook|zenbook|expertbook|\btuf\b|\brog\b|ideapad|thinkpad|thinkbook|\blegion\b|\bloq\b|yoga|"
    r"pavilion|victus|\bomen\b|elitebook|probook|aspire|\bnitro\b|helios|triton|\bswift\b|inspiron|vostro|"
    r"latitude|\bxps\b|alienware|\bmonster\b|\babra\b|tulpar|casper|excalibur|matebook|katana|cyborg|"
    r"msi (thin|modern|prestige|sword|crosshair|vector|raider)|galaxy book|surface|chromebook|"
    r"\b(1[0-9]|2[0-9]|3[0-9])([.,]\d)?\s?(\"|inc|inch|ekran)|\d{3}\s?hz|\bfhd\b|\bqhd\b|\boled\b|\bips\b|"
    r"kutu|enclosure|adapt[oö]r|so[gğ]utucu|heatsink|kizak|\bdock\b")

def is_ssd(title):
    t = norm(title)
    return bool(POS.search(t)) and not NEG.search(t)

# ---------------------------------------------------------------- forum
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")

def threads(page):
    out = []
    for m in re.finditer(r'<div class="structItem-title"[^>]*>(.*?)</div>', page, re.S):
        for a in re.finditer(r'<a href="(/konu/[^"]+?\.(\d+)/)"[^>]*>(.*?)</a>', m.group(1), re.S):
            title = html.unescape(re.sub("<[^>]+>", "", a.group(3))).strip()
            if title:
                out.append((a.group(2), title, BASE + a.group(1)))
    return out

# ---------------------------------------------------------------- bildirim
def post(url, data, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status

def notify(title, link=""):
    sent = False
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    topic = os.environ.get("NTFY_TOPIC")
    for _ in range(3):
        try:
            if tok and chat:
                text = title + ("\n" + link if link else "")
                post("https://api.telegram.org/bot%s/sendMessage" % tok,
                     urllib.parse.urlencode({"chat_id": chat, "text": text}).encode())
            if topic:
                h = {"Title": "SSD firsati", "Priority": "high", "Tags": "floppy_disk"}
                if link:
                    h["Click"] = link
                post("https://ntfy.sh/" + topic, (title + ("\n" + link if link else "")).encode("utf-8"), h)
            sent = True
            break
        except Exception as e:
            print("bildirim hatasi:", e, flush=True)
            time.sleep(3)
    print(("GONDERILDI " if sent else "GONDERILEMEDI ") + title + " " + link, flush=True)

# ---------------------------------------------------------------- durum
def load_seen():
    try:
        return json.load(open(SEEN))
    except Exception:
        return None

def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    keep = sorted(set(seen), key=int)[-3000:]
    with open(SEEN, "w") as f:
        json.dump(keep, f)
    if os.environ.get("NO_GIT") == "1":
        return
    try:
        subprocess.run(["git", "add", SEEN], cwd=DIR, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=DIR).returncode != 0:
            subprocess.run(["git", "commit", "-q", "-m", "durum guncellendi"], cwd=DIR, check=True)
            subprocess.run(["git", "pull", "-q", "--rebase", "-X", "theirs"], cwd=DIR)
            subprocess.run(["git", "push", "-q"], cwd=DIR, check=True)
    except Exception as e:
        print("git hatasi:", e, flush=True)

# ---------------------------------------------------------------- ana dongu
def main():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        for t in sys.argv[2:]:
            print(is_ssd(t), t)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "ping":
        notify("Test bildirimi: SSD takip botu calisiyor", URL)
        return

    has_notify = os.environ.get("NTFY_TOPIC") or (
        os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    if not has_notify and os.environ.get("NO_GIT") != "1":
        print("HATA: NTFY_TOPIC veya TELEGRAM_* secret'i tanimli degil. "
              "Repo > Settings > Secrets and variables > Actions bolumunden ekle.", flush=True)
        sys.exit(1)

    seen_list = load_seen()
    first = seen_list is None
    seen = set(seen_list or [])
    start = last_save = time.time()
    dirty = first
    fails = 0
    print("basladi, ilk calisma" if first else "basladi, %d konu biliniyor" % len(seen), flush=True)

    while time.time() - start < RUN_SECONDS:
        try:
            found = threads(fetch(URL))
            if not found:
                raise RuntimeError("sayfada konu bulunamadi")
            for tid, title, link in found:
                if tid in seen:
                    continue
                seen.add(tid)
                dirty = True
                if is_ssd(title):
                    if first:
                        print("mevcut SSD konusu (bildirilmedi):", title, flush=True)
                    else:
                        notify(title, link)
                else:
                    print("atlandi:", title, flush=True)
            first = False
            if fails >= 20:
                notify("Forum tekrar okunabiliyor, takip devam ediyor")
            fails = 0
        except Exception as e:
            fails += 1
            print("okuma hatasi:", e, flush=True)
            if fails == 20:
                notify("UYARI: Forum ~5 dakikadir okunamiyor (%s)" % str(e)[:100], URL)
        if dirty and time.time() - last_save > SAVE_EVERY:
            save_seen(seen)
            dirty, last_save = False, time.time()
        time.sleep(INTERVAL)

    save_seen(seen)
    print("sure doldu, sonraki calistirma devralacak", flush=True)

if __name__ == "__main__":
    main()
