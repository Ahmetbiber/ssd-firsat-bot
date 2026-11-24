#!/usr/bin/env python3
"""DonanimArsivi -> yeni SSD firsati gorulunce telefona bildirim.

Izlenenler:
  1) Sicak Fırsatlar bolumu, INTERVAL saniyede bir (yeni konular)
  2) Tum forumun "Yeni mesajlar" sayfasi, dakikada bir:
     - baska bolumlerde acilan yeni konular (baslikta fiyat olmali, soru olmamali)
     - firsat/alisveris konularina yazilan yeni cevaplar (ayni satirda SSD + fiyat)

Ortam degiskenleri:
  NTFY_TOPIC                              -> ntfy.sh bildirimi
  TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID   -> Telegram bildirimi
  RUN_SECONDS  kac saniye calissin (varsayilan: sinirsiz)
  INTERVAL     Sicak Fırsatlar kontrol araligi, sn (varsayilan 15)
  NO_GIT=1     durum dosyasini git'e commit'leme (kendi cihazinda calistirirken)

Kullanim:
  python3 bot.py                 izlemeyi baslat
  python3 bot.py test "baslik"   baslik filtresini dene
  python3 bot.py line "satir"    mesaj satiri filtresini dene
  python3 bot.py ping            test bildirimi gonder
"""
import html, json, os, re, subprocess, sys, time, unicodedata, urllib.parse, urllib.request

BASE = "https://forum.donanimarsivi.com"
URL = BASE + "/forumlar/Sicakfirsatlar/?order=post_date&direction=desc"
WHATS_NEW = BASE + "/whats-new/posts/"
DIR = os.path.dirname(os.path.abspath(__file__))
SEEN = os.path.join(DIR, "state", "seen.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "0")) or 10 ** 9
INTERVAL = int(os.environ.get("INTERVAL", "15"))
WN_EVERY = 60
SAVE_EVERY = 120
DEAL_FORUM = re.compile(r"f[iı]rsat|al[iı][sş]veri[sş]|sat[iı]l[iı]k|pazar|ikinci el|kampanya|indirim", re.I)

# ---------------------------------------------------------------- filtre
TR = str.maketrans("çşğüöı", "csguoi")
# Magaza adlari ("Vatan PC", "Vatan Bilgisayar") urunle karismasin
STORES = re.compile(r"\b(vatan|sinerji|tek|gaming ?gen|inceh?esap|ebrar)\s?(pc|bilgisayar)\w*")

def norm(t):
    t = unicodedata.normalize("NFKC", t)       # 𝑲𝑰𝑶𝑿𝑰𝑨 gibi suslu yazilari duzelt
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

# Fiyat / satis isareti (baska bolumlerdeki basliklar ve mesaj satirlari icin)
PRICE = re.compile(r"\d[\d.,]*\s?(tl|₺|lira|try)\b|₺|\d[\d.,]*\s?(tl|₺)|\bsatilik\b|\bfiyat\w*\b.{0,15}\d")
# Soru / tavsiye konusu -> fırsat degil
QUESTION = re.compile(r"\?|\bhangi\b|\bnasil|\boneri|\btavsiye|\bsorun|\byardim|\bmi\b|\bmu\b|\bmisiniz\b|"
                      r"\bmantikli\b|\bdeger mi|\balinir mi|\bvs\b|\bsecim")

def is_ssd_deal_title(title, forum):
    """Sicak Fırsatlar disindaki basliklar: SSD + fiyat, soru degil."""
    if forum and DEAL_FORUM.search(forum):
        return is_ssd(title)
    t = norm(title)
    return is_ssd(title) and bool(PRICE.search(t)) and not QUESTION.search(t)

def is_ssd_deal_line(line):
    t = norm(line)
    return is_ssd(line) and bool(PRICE.search(t)) and not QUESTION.search(t)

# ---------------------------------------------------------------- forum
def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "tr"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace"), r.geturl()

def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()

def threads(page):
    """Konu listesi -> [{id, title, link, forum, latest}]"""
    out = []
    for part in re.split(r'<div class="structItem structItem--thread', page)[1:]:
        a = re.search(r'<div class="structItem-title"[^>]*>.*?<a href="(/konu/[^"]+?\.(\d+)/)"[^>]*>(.*?)</a>', part, re.S)
        if not a:
            continue
        f = re.findall(r'<a href="/forumlar/[^"]+"[^>]*>([^<]*)</a>', part)
        lt = re.search(r'structItem-latestDate[^>]*data-timestamp="(\d+)"', part)
        out.append({"id": a.group(2), "title": re.sub(r"\s+", " ", clean(a.group(3))),
                    "link": BASE + a.group(1), "forum": html.unescape(f[-1]) if f else "",
                    "latest": int(lt.group(1)) if lt else 0})
    return out

def posts(page):
    """Konu sayfasi -> [(post_id, timestamp, satirlar)]; alintilar ve imzalar haric."""
    out = []
    for part in re.split(r'<article class="message message--post', page)[1:]:
        pid = re.search(r'data-content="post-(\d+)"', part)
        ts = re.search(r'data-timestamp="(\d+)"', part)
        body = re.search(r'<div class="bbWrapper">(.*?)</div>\s*<div class="js-selectToQuote', part, re.S)
        if not (pid and body):
            continue
        b = re.sub(r"<blockquote.*?</blockquote>", " ", body.group(1), flags=re.S)
        b = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", b)
        lines = [re.sub(r"\s+", " ", clean(l)) for l in b.split("\n")]
        out.append((int(pid.group(1)), int(ts.group(1)) if ts else 0, [l for l in lines if l]))
    return out

# ---------------------------------------------------------------- bildirim
def post(url, data, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status

def notify(title, link="", head="SSD firsati"):
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    topic = os.environ.get("NTFY_TOPIC")
    text = title + ("\n" + link if link else "")
    ok = True
    if tok and chat:
        ok &= send(lambda: post("https://api.telegram.org/bot%s/sendMessage" % tok,
                                urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()))
    if topic:
        h = {"Title": head, "Priority": "high", "Tags": "floppy_disk"}
        if link:
            h["Click"] = link
        ok &= send(lambda: post("https://ntfy.sh/" + topic, text.encode("utf-8"), h))
    print(("GONDERILDI " if ok else "GONDERILEMEDI ") + text.replace("\n", " "), flush=True)

def send(fn):
    for i in range(4):
        try:
            fn()
            return True
        except Exception as e:
            print("bildirim hatasi:", e, flush=True)
            time.sleep(3 * (i + 1))
    return False

# ---------------------------------------------------------------- durum
def load_state():
    try:
        d = json.load(open(SEEN))
    except Exception:
        return None
    if isinstance(d, list):                     # eski bicim: sadece konu id listesi
        d = {"threads": d}
    if not d.get("threads"):
        return None
    d.setdefault("latest", {})
    d.setdefault("maxpost", {})
    return d

def save_state(st):
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    keep = sorted(set(st["threads"]), key=int)[-5000:]
    recent = set(sorted(st["latest"], key=int)[-500:])
    d = {"threads": keep,
         "latest": {k: v for k, v in st["latest"].items() if k in recent},
         "maxpost": {k: v for k, v in st["maxpost"].items() if k in recent}}
    with open(SEEN + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(SEEN + ".tmp", SEEN)
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

def git_out(*args):
    if os.environ.get("NO_GIT") == "1":
        return None
    try:
        r = subprocess.run(["git"] + list(args), cwd=DIR, capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None

# ---------------------------------------------------------------- izleyici
class Watcher:
    def __init__(self):
        st = load_state()
        self.first = st is None
        self.st = st or {"threads": [], "latest": {}, "maxpost": {}}
        self.seen = set(self.st["threads"])
        self.dirty = self.first
        # tum forum ilk kez taraniyorsa diger bolumlerin eski konularini sessizce kaydet
        self.wn_first = not self.st["latest"]
        self.fail_since, self.alerted, self.slow = None, False, 0
        print("basladi, ilk calisma" if self.first else "basladi, %d konu biliniyor" % len(self.seen), flush=True)

    def new_thread(self, t, from_deals):
        if t["id"] in self.seen:
            return
        self.seen.add(t["id"])
        self.dirty = True
        hit = is_ssd(t["title"]) if from_deals else is_ssd_deal_title(t["title"], t["forum"])
        tag = "SSD" if hit else "atlandi"
        print("%s %s|%s|%s|%s" % (time.strftime("%H:%M:%S"), tag, t["forum"] or "Sicak Firsatlar",
                                  t["title"], t["link"]), flush=True)
        quiet = self.first or (self.wn_first and not from_deals and not DEAL_FORUM.search(t["forum"]))
        if hit and not quiet:
            where = "" if from_deals or "rsat" in t["forum"] else " [%s]" % t["forum"]
            notify(t["title"] + where, t["link"])

    def check_deals(self):
        page, _ = fetch(URL)
        found = threads(page)
        if not found:
            raise RuntimeError("Sicak Fırsatlar sayfasinda konu bulunamadi")
        for t in found:
            self.new_thread(t, True)

    def check_whats_new(self):
        page, _ = fetch(WHATS_NEW)
        found = threads(page)
        if not found:
            raise RuntimeError("Yeni mesajlar sayfasinda konu bulunamadi")
        for t in found:
            known = t["id"] in self.seen or self.wn_first
            self.new_thread(t, False)
            prev = self.st["latest"].get(t["id"])
            self.st["latest"][t["id"]] = t["latest"]
            if not known or prev is None or t["latest"] <= prev:
                continue                       # yeni konu ya da cevap yok
            if not DEAL_FORUM.search(t["forum"]) or is_ssd(t["title"]):
                continue                       # sadece firsat konularindaki cevaplar; SSD konusu zaten bildirildi
            self.check_replies(t, prev)
        self.wn_first = False

    def check_replies(self, t, prev_ts):
        page, final = fetch(t["link"] + "latest")
        base = final.split("#")[0]
        last = self.st["maxpost"].get(t["id"], 0)
        for pid, ts, lines in posts(page):
            if pid <= last or ts <= prev_ts:
                continue
            for line in lines:
                if is_ssd_deal_line(line):
                    print("%s SSD-mesaj|%s|%s|%s#post-%d" % (time.strftime("%H:%M:%S"), t["title"], line, base, pid), flush=True)
                    notify("Mesajda: " + line[:150] + "\n(" + t["title"][:60] + ")", "%s#post-%d" % (base, pid))
                    break
            last = max(last, pid)
        self.st["maxpost"][t["id"]] = last
        self.dirty = True

    def guarded(self, fn):
        try:
            fn()
            if self.alerted:
                notify("Forum tekrar okunabiliyor, takip devam ediyor", head="SSD takip")
            self.fail_since, self.alerted, self.slow = None, False, 0
        except Exception as e:
            code = getattr(e, "code", None)
            self.fail_since = self.fail_since or time.time()
            # forum "yavasla/engel" derse kendini yavaslat: 30s, 60s ... en fazla ~8 dk
            self.slow = min(self.slow + 1, 5) if code in (403, 429, 503) else min(self.slow, 2)
            print("%s okuma hatasi: %r" % (time.strftime("%H:%M:%S"), e), flush=True)
            if not self.alerted and time.time() - self.fail_since > 300:
                notify("UYARI: Forum ~5 dakikadir okunamiyor (%s)" % str(e)[:100], URL, head="SSD takip")
                self.alerted = True

    def save(self):
        self.st["threads"] = list(self.seen)
        save_state(self.st)
        self.dirty = False

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("test", "line"):
        f = is_ssd if sys.argv[1] == "test" else is_ssd_deal_line
        for t in sys.argv[2:]:
            print(f(t), t)
        return
    if len(sys.argv) > 1 and sys.argv[1] == "ping":
        notify("Test bildirimi: SSD takip botu calisiyor", BASE, head="SSD takip")
        return

    has_notify = os.environ.get("NTFY_TOPIC") or (
        os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))
    if not has_notify:
        print("UYARI: NTFY_TOPIC / TELEGRAM_* tanimli degil, bildirim gonderilmeyecek.", flush=True)
        if os.environ.get("NO_GIT") != "1":
            sys.exit(1)

    w = Watcher()
    start = last_save = last_upd = time.time()
    last_wn = 0
    start_sha = git_out("rev-parse", "HEAD")
    while time.time() - start < RUN_SECONDS:
        w.guarded(w.check_deals)
        if time.time() - last_wn >= WN_EVERY:
            last_wn = time.time()
            w.guarded(w.check_whats_new)
        w.first = False
        if w.dirty and time.time() - last_save > SAVE_EVERY:
            w.save()
            last_save = time.time()
        # repoda yeni kod varsa kaydet ve cik (GitHub'da calisirken)
        if start_sha and time.time() - last_upd > 60:
            last_upd = time.time()
            if git_out("fetch", "-q", "origin", "main") is not None and \
               git_out("diff", "--name-only", start_sha, "FETCH_HEAD", "--", "bot.py", ".github"):
                print("yeni kod bulundu, yeniden baslatiliyor", flush=True)
                break
        time.sleep(INTERVAL * (2 ** w.slow))
    w.save()
    print("calisma bitti", flush=True)

if __name__ == "__main__":
    main()
