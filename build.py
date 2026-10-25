#!/usr/bin/env python3
"""Builds kvp-projects.com into docs/ (GitHub Pages serves that folder).

Reads content.json (texts) and the kvp registry ../spec/products.json (ids, feeds, paths), each product's CHANGELOG.md (and CHANGELOG.en.md when it has one) and the update feeds in
../updates (the newest released version → the download link). Run after a release or a change in content.json:
    python3 build.py
Products are found through the registry: ~/Проекты/kvp/<product>/<platform>/ (this folder is kvp/core/site).
The look — the design on claude.ai (canvas «kvp-projects.com»): white paper, dark ink, pencil frames drawn like
Dictum's pencil style (pencil.py).
"""
import datetime, email.utils, functools, html, json, os, re, shutil, subprocess, sys, urllib.parse
import xml.etree.ElementTree as ET

import pencil

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
DOMAIN = "kvp-projects.com"
RELEASES = "https://updates.kvp-projects.com/files"   # our server (docs/updates-server.md); GitHub Releases is the archive
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"

T = {
    "ru": {
        "title": "kvp projects", "h1": "Маленькие программы,<br>которые экономят время",
        "lead": "Говорить вместо того, чтобы печатать. Находить скопированное неделю назад. Считать прямо в заметке. Для Mac и браузера.",
        "updates": "Обновления", "rss": "RSS", "fresh": "Свежие обновления", "allUpdates": "Все обновления →",
        "updated": "Обновлено · {v}", "newIn": "Новое в {v}", "gains": "Что даёт",
        "updatesLead": "Что нового во всех программах — по датам. Обновления приходят сами: программа предложит их установить.",
        "subscribe": "Подписаться через RSS", "filter": "Показать обновления", "allChip": "Все",
        "more": "+ ещё {n}", "details": "Подробнее и скачать", "appUpdates": "Все обновления {name}", "inRu": "",
        "rssTitle": "kvp projects — обновления", "rssDesc": "Новые версии программ kvp projects для Mac.",
        "download": "Скачать для Mac", "soon": "Скоро", "store": "Установить из Chrome Web Store",
        "chromeSoon": "Скоро в Chrome Web Store", "requires": "{min} или новее",
        "beta": "Бета", "betaNote": "Бета-версия: приложение активно развивается, возможности ещё добавляются.",
        "version": "Версия {v}", "features": "Что умеет", "changes": "Что нового", "older": "Предыдущие версии",
        "all": "Все программы", "noEn": "", "langSwitch": "English", "next": "Скоро — {list}.",
        "notFound": "Такой страницы нет", "home": "На главную", "author": "Кирилл Прудников", "contact": "Написать мне",
        "activateTitle": "Активация лицензии", "activateLead": "Нажми кнопку — приложение откроется, и ключ вставится сам. Если приложения на этом Mac нет, скачай его и нажми кнопку ещё раз или скопируй ключ и вставь вручную.",
        "openIn": "Открыть {name}", "copy": "Скопировать ключ", "copied": "Скопировано", "copyManually": "Ключ выделен — нажми ⌘C",
        "noKey": "В ссылке нет ключа или он повреждён — открой ссылку из письма ещё раз.",
        "unknownApp": "Ссылка указывает на приложение, которого я не знаю. Выбери своё приложение ниже.",
        "paste": "Вручную: {path}", "downloadApp": "страница {name}",
        "uiRuOnly": "Интерфейс: только русский", "privacy": "Конфиденциальность",
        "uninstall": "Как удалить", "uninstallMenu": "В приложении: меню {name} → «Удалить {name}…» (или {settings}).",
        "uninstallSettings": "Настройки → О программе", "uninstallKeepLabel": "Оставить мои данные и настройки",
        "uninstallKeep": "Собираешься вернуться — поставь галочку «{label}»: поставишь {name} снова, и всё будет на месте.",
        "uninstallSince": "Эта кнопка есть в версиях новее {v}.", "uninstallFrom": "Эта кнопка есть с версии {v}.",
        "uninstallManual": "Вручную (для старых версий)",
        "uninstallManualLead": "Открой Терминал, вставь строку и нажми Return. Она закроет {name} и удалит его вместе с данными.",
        "copyCmd": "Скопировать", "copiedCmd": "Скопировано",
        "sections": {"mac": ("Для Mac", "macOS"), "chrome": ("Для браузера", "Google Chrome"), "windows": ("Для Windows", ""),
                     "linux": ("Для Linux", ""), "ios": ("Для iPhone и iPad", "iOS"), "android": ("Для Android", "")},
    },
    "en": {
        "title": "kvp projects", "h1": "Small apps<br>that save you time",
        "lead": "Speak instead of typing. Find what you copied a week ago. Do the math right in your notes. For Mac and the browser.",
        "updates": "Updates", "rss": "RSS", "fresh": "Latest updates", "allUpdates": "All updates →",
        "updated": "Updated · {v}", "newIn": "New in {v}", "gains": "What you get",
        "updatesLead": "What’s new in every app, by date. Updates arrive on their own: the app offers to install them.",
        "subscribe": "Subscribe via RSS", "filter": "Show updates", "allChip": "All",
        "more": "+ {n} more", "details": "Details and download", "appUpdates": "All {name} updates", "inRu": "in Russian",
        "rssTitle": "kvp projects — updates", "rssDesc": "New versions of kvp projects apps for Mac.",
        "download": "Download for Mac", "soon": "Coming soon", "store": "Add from Chrome Web Store",
        "chromeSoon": "Coming soon to Chrome Web Store", "requires": "{min} or later",
        "beta": "Beta", "betaNote": "Beta: the app is in active development, more is on the way.",
        "version": "Version {v}", "features": "Features", "changes": "What’s new", "older": "Earlier versions",
        "all": "All apps", "noEn": "The change history is in Russian.", "langSwitch": "Русский",
        "next": "Coming next: {list}.", "notFound": "Page not found", "home": "Home", "author": "Kirill Prudnikov", "contact": "Contact me",
        "activateTitle": "License activation", "activateLead": "Press the button — the app opens and the key goes in by itself. If the app isn’t on this Mac, download it and press the button again, or copy the key and paste it yourself.",
        "openIn": "Open {name}", "copy": "Copy Key", "copied": "Copied", "copyManually": "The key is selected — press ⌘C",
        "noKey": "There’s no key in this link, or it’s damaged — open the link from the email again.",
        "unknownApp": "This link points to an app I don’t know. Choose your app below.",
        "paste": "By hand: {path}", "downloadApp": "{name} page",
        "uiRuOnly": "Interface: Russian only", "privacy": "Privacy",
        "uninstall": "How to uninstall", "uninstallMenu": "In the app: {name} menu → «Uninstall {name}…» (or {settings}).",
        "uninstallSettings": "Settings → About", "uninstallKeepLabel": "Keep my data and settings",
        "uninstallKeep": "Planning to come back? Tick «{label}» — install {name} again and everything will be there.",
        "uninstallSince": "This is in versions newer than {v}.", "uninstallFrom": "This is in version {v} and later.",
        "uninstallManual": "By hand (for older versions)",
        "uninstallManualLead": "Open Terminal, paste the line and press Return. It quits {name} and deletes it along with its data.",
        "copyCmd": "Copy", "copiedCmd": "Copied",
        "sections": {"mac": ("For Mac", "macOS"), "chrome": ("For the browser", "Google Chrome"), "windows": ("For Windows", ""),
                     "linux": ("For Linux", ""), "ios": ("For iPhone and iPad", "iOS"), "android": ("For Android", "")},
    },
}
PLATFORM = {"mac": "macOS", "chrome": "Chrome", "windows": "Windows", "linux": "Linux", "ios": "iOS", "android": "Android"}

# The privacy page (/privacy/, /en/privacy/). Keep it true to the code: every network request the apps make is here.
PRIVACY = {
    "ru": {
        "title": "Конфиденциальность",
        "lead": "Коротко: мои приложения работают на твоём Mac и ничего о тебе не собирают. Ниже — всё, что они отправляют в интернет, и зачем.",
        "sections": [
            ("Твои данные остаются на Mac", [
                "Заметки, история буфера обмена, снимки и записи экрана, диктовки, тексты и настройки хранятся только на твоём компьютере. Я их не вижу и никуда не загружаю."]),
            ("Отчёты об ошибках — по желанию", [
                "Если в приложении что-то сломалось, оно может отправить отчёт, чтобы я нашёл и исправил ошибку. Отчёты отправляются только с твоего согласия: приложение спрашивает об этом при первом запуске, а выключить их можно в настройках в любой момент.",
                "В отчёте — версия приложения и macOS, сведения о Mac (процессор, память, свободное место) и служебные записи о том, что происходило перед ошибкой. Твоих текстов, диктовок, файлов, снимков и ключей там нет; путь к твоей домашней папке заменяется на «~».",
                "Отчёт идёт через мой сервер reports.kvp-projects.com в сервис Sentry (данные хранятся в ЕС). Мой сервер не передаёт дальше твой IP-адрес, а Sentry настроен IP-адреса не хранить."]),
            ("Обновления и лицензия", [
                "Раз в день приложение проверяет, нет ли новой версии, и читает файл с правилами лицензий на updates.kvp-projects.com. Это обычное скачивание файла: о тебе и о том, как ты пользуешься приложением, ничего не отправляется. Как и любой сайт, сервер видит адрес, с которого пришёл запрос. Новая версия ставится только с твоего согласия, автоматическую проверку можно выключить в настройках. Сами файлы приложений скачиваются оттуда же — с моего сервера; журнал обращений к нему не ведётся.",
                "Лицензионный ключ содержит почту, на которую он выдан, и проверяется прямо на Mac, без связи с сервером. В ссылке активации ключ стоит после знака «#» — браузер не отправляет эту часть адреса на сервер."]),
            ("Что отправляют отдельные приложения", [
                "<b>Dictum.</b> По умолчанию речь распознаётся прямо на Mac; модели для этого один раз скачиваются с сайта Hugging Face. Если ты выберешь облачное распознавание (OpenAI, Groq, Deepgram, ElevenLabs) или обработку текста ИИ (Anthropic, OpenAI, Groq), запись или текст уходят в выбранный тобой сервис с твоим собственным ключом и по его правилам. Ollama, LM Studio и модель Apple работают на твоём Mac. Встроенное распознавание Apple работает по правилам Apple.",
                "<b>Textum.</b> ИИ-действия отправляют выделенный текст и команду в Anthropic (Claude) с твоим собственным ключом — или обрабатывают его моделью Apple прямо на Mac. Для пересчёта валют загружаются курсы с open.er-api.com — без твоих данных.",
                "<b>Note Calc.</b> Для валют загружает курсы с open.er-api.com — без твоих данных.",
                "<b>Cliplark и Shotlark</b> кроме описанного выше в интернет ничего не отправляют."]),
            ("Этот сайт", [
                "Без аналитики, рекламы и cookies; шрифты загружаются с самого сайта. Сайт размещён на GitHub Pages — GitHub, как любой хостинг, видит технические данные запросов, например IP-адрес."]),
            ("Вопросы", ["Если что-то непонятно или хочешь, чтобы я удалил отчёты, связанные с тобой, — {contact}."]),
        ],
        "contact": "напиши мне",
    },
    "en": {
        "title": "Privacy",
        "lead": "In short: my apps work on your Mac and don’t collect anything about you. Below is everything they send over the internet, and why.",
        "sections": [
            ("Your data stays on your Mac", [
                "Notes, clipboard history, screenshots and screen recordings, dictations, texts and settings are kept only on your computer. I can’t see them and don’t upload them anywhere."]),
            ("Error reports — if you want", [
                "When something breaks, an app can send a report so I can find and fix the bug. Reports are sent only with your consent: the app asks on first launch, and you can turn them off in its settings at any time.",
                "A report contains the app and macOS versions, details about the Mac (processor, memory, free space) and technical notes about what happened before the error. It never includes your texts, dictations, files, screenshots or keys; the path to your home folder is replaced with “~”.",
                "Reports go through my server reports.kvp-projects.com to Sentry (data stored in the EU). My server doesn’t pass your IP address on, and Sentry is set not to store IP addresses."]),
            ("Updates and licenses", [
                "Once a day an app checks for a new version and reads the license policy file on updates.kvp-projects.com. It’s a plain file download: nothing about you or how you use the app is sent. Like any website, the server sees the address the request came from. A new version is installed only with your consent, and automatic checks can be turned off in settings. The app files themselves come from there too — my own server, which keeps no access log.",
                "A license key contains the email it was issued to and is checked right on your Mac, without contacting a server. In an activation link the key comes after the “#” sign — browsers never send that part of the address to a server."]),
            ("What individual apps send", [
                "<b>Dictum.</b> By default speech is recognized right on your Mac; the models are downloaded once from Hugging Face. If you choose cloud recognition (OpenAI, Groq, Deepgram, ElevenLabs) or AI text processing (Anthropic, OpenAI, Groq), the recording or text goes to the service you chose, with your own key and under its terms. Ollama, LM Studio and Apple’s model run on your Mac. Apple’s built-in recognition works under Apple’s terms.",
                "<b>Textum.</b> AI actions send the selected text and the command to Anthropic (Claude) with your own key — or process it with Apple’s model right on your Mac. Currency conversion downloads exchange rates from open.er-api.com, without any of your data.",
                "<b>Note Calc.</b> Downloads exchange rates for currencies from open.er-api.com, without any of your data.",
                "<b>Cliplark and Shotlark</b> send nothing beyond what is described above."]),
            ("This website", [
                "No analytics, ads or cookies; fonts are served by the site itself. The site is hosted on GitHub Pages — like any host, GitHub sees technical request data such as the IP address."]),
            ("Questions", ["If something is unclear, or you’d like me to delete reports related to you, {contact}."]),
        ],
        "contact": "write to me",
    },
}

e = html.escape


def rel(p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(ROOT, p))


def parse_changelog(path):
    """Keep a Changelog, the shelf's rules: [{version|None, date, sections: [{title, items}]}], newest first."""
    if not path or not os.path.exists(rel(path)):
        return None
    out, cur, sec = [], None, None
    for raw in open(rel(path), encoding="utf-8").read().splitlines():
        line = raw.strip()
        if line.startswith("## "):
            head = line[3:].replace("[", "").replace("]", "")
            first = head.split(" ")[0]
            date = re.search(r"\d{4}-\d{2}-\d{2}", head)
            cur = {"version": first if re.fullmatch(r"\d+(\.\d+)*", first) else None, "date": date.group(0) if date else None, "sections": []}
            out.append(cur)
            sec = None
        elif line.startswith("### ") and cur is not None:
            sec = {"title": line[4:].strip(), "items": []}
            cur["sections"].append(sec)
        elif line.startswith(("- ", "* ")) and cur is not None:
            if sec is None:
                sec = {"title": "", "items": []}
                cur["sections"].append(sec)
            sec["items"].append(line[2:].strip())
        elif line and raw.startswith("  ") and sec and sec["items"]:
            sec["items"][-1] += " " + line
    return [r for r in out if any(s["items"] for s in r["sections"])]


def inline(s):
    s = e(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    return re.sub(r"`(.+?)`", r"<code>\1</code>", s)


@functools.lru_cache(maxsize=None)
def latest_mac(feed):
    """The newest PUBLISHED version in the app's update feed: ../updates/<feed>/appcast.xml (or note-calc's latest.json)
    as committed in the updates repo (HEAD), not the working tree — release.sh writes feeds there before publish.sh
    uploads the files, and the site must never link to a download that isn't on the update server yet. None before the first release."""
    updates = os.path.join(ROOT, "..", "updates")
    def committed(name):
        r = subprocess.run(["git", "-C", updates, "show", f"HEAD:{feed}/{name}"], capture_output=True)
        return r.stdout if r.returncode == 0 else None
    tauri = committed("latest.json")   # note-calc: Tauri's updater feed
    if tauri is not None:
        return json.loads(tauri).get("version")
    xml = committed("appcast.xml")
    if xml is None:
        return None
    items = ET.fromstring(xml).findall("./channel/item")
    versions = [v for v in (i.findtext(SPARKLE + "shortVersionString") for i in items) if v]
    return max(versions, key=lambda v: [int(x) for x in v.split(".")]) if versions else None


@functools.lru_cache(maxsize=None)
def feed_history(feed):
    """Every version that ever appeared in the app's COMMITTED feed (the updates repo's git history, not the working
    tree): {version: when it first appeared — that commit's time, UTC}. One `git log -p` per feed; only that makes a
    version published (release.sh may write a feed that publish.sh never commits)."""
    updates = os.path.join(ROOT, "..", "updates")
    for name, pattern in (("latest.json", r'"version"\s*:\s*"([^"]+)"'),          # note-calc: Tauri's updater feed
                          ("appcast.xml", r"<sparkle:shortVersionString>([^<]+)<")):
        r = subprocess.run(["git", "-C", updates, "log", "--reverse", "-p", "--format=\x01%ct", "--", f"{feed}/{name}"],
                           capture_output=True, text=True)
        out, when = {}, None
        for line in (r.stdout if r.returncode == 0 else "").splitlines():
            if line.startswith("\x01"):
                when = datetime.datetime.fromtimestamp(int(line[1:]), datetime.timezone.utc)
            elif line.startswith("+") and not line.startswith("+++"):
                for v in re.findall(pattern, line):
                    out.setdefault(v.strip(), when)
        if out:
            return out
    return {}


def num(v):
    return [int(x) for x in v.split(".")]


MONTHS = {"ru": ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"),
          "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")}


def day(iso, lang, short=False):
    """2026-10-11 → «11 октября 2026» / «11 окт» (short), "October 11, 2026" / "Oct 11"."""
    if not iso:
        return ""
    y, m, d = (int(x) for x in iso.split("-"))
    month = MONTHS[lang][m - 1]
    if lang == "ru":
        return f"{d} {month[:3] if short and month != 'мая' else month}" + ("" if short else f" {y}")
    return f"{month[:3]} {d}" if short else f"{month} {d}, {y}"


def mac_platform(p):
    return next((pl for pl in p.get("platforms", []) if pl["kind"] == "mac"), None)


def fold(release, older):
    """`release` with the items of `older` (versions never published, newest first) added: same section title — appended
    to it, a new title — a new section at the end. People got all of it at once, with this version."""
    secs = [{"title": s["title"], "items": list(s["items"])} for s in release["sections"]]
    for o in older:
        for s in o["sections"]:
            same = next((x for x in secs if x["title"] == s["title"]), None)
            if same:
                same["items"] += s["items"]
            else:
                secs.append({"title": s["title"], "items": list(s["items"])})
    return {**release, "sections": secs}


_releases = {}


def releases(p, lang):
    """The product's released versions, newest first, and whether they are the Russian log on an English page (no
    changelog_en: shown in Russian, marked so — the same on the product page, /updates/ and the feed).
    A Mac app: a version counts only if it ever appeared in its committed feed history (feed_history) — the site never
    runs ahead of «Download». A version that never did (cut, but not given to people) isn't shown on its own: its items
    fold into the next published version; versions after the newest published one wait. Each release of a Mac app
    gets `published` — when it first appeared in the feed (the RSS pubDate)."""
    key = (p["id"], lang)
    if key in _releases:
        return _releases[key]
    log = parse_changelog(p.get("changelog_en")) if lang == "en" else None
    ru_only = lang == "en" and log is None
    if log is None:
        log = parse_changelog(p.get("changelog"))
    released = [r for r in (log or []) if r["version"]]
    mac = mac_platform(p)
    if mac:
        history, out, pending = feed_history(mac["feed"]), [], []
        for r in reversed(released):                      # oldest first
            if r["version"] in history:
                out.append({**fold(r, pending[::-1]), "published": history[r["version"]]})
                pending = []
            else:
                pending.append(r)
        released = out[::-1]
    _releases[key] = (released, ru_only)
    return _releases[key]


def items(r):
    return [i for s in r["sections"] for i in s["items"]]


def headline(p, r, lang, ru_only):
    """One line of news for a release: the changelog's first item (CHANGELOG-RULES: the most notable comes first), or,
    for versions released before that rule, `headlines` in content.json ({"0.4.0": {"ru": …, "en": …}}).
    Returns (text, ru_only of that text)."""
    h = (p.get("headlines") or {}).get(r["version"])
    if h:
        return (h.get(lang) or h["ru"]), (lang == "en" and not h.get("en"))
    return items(r)[0], ru_only


def feed(data, lang):
    """Every published release of every Mac app, newest first: [(product, release, ru_only)]. Same day — content.json
    order, then the newer version first."""
    out = []
    for idx, p in enumerate(data):
        if mac_platform(p):
            rs, ru_only = releases(p, lang)
            out += [(idx, p, r, ru_only) for r in rs]
    out.sort(key=lambda x: (x[2]["date"] or "", -x[0], num(x[2]["version"])), reverse=True)
    return [(p, r, ru) for _, p, r, ru in out]


def ru_attr(ru_only):
    return ' lang="ru"' if ru_only else ""


def make_icon(p):
    icon = p["icon"]
    dest = os.path.join(OUT, "assets", "icons", p["id"] + ".png")
    src = next((rel(icon[k]) for k in ("icns", "fallback", "png") if icon.get(k) and os.path.exists(rel(icon[k]))), None)
    if not src:
        sys.exit(f"❌ нет значка для {p['id']}")
    subprocess.run(["sips", "-s", "format", "png", "--resampleHeightWidthMax", "288", src, "--out", dest],
                   check=True, capture_output=True)
    return "assets/icons/" + os.path.basename(dest)


def beta(p, lang):
    """The «Бета» mark: every product until content.json says "beta": false (a 1.0 release)."""
    return f' <span class="beta">{T[lang]["beta"]}</span>' if p.get("beta", True) else ""


def beta_note(p, lang):
    return f'<p class="meta beta-note">{T[lang]["betaNote"]}</p>' if p.get("beta", True) else ""


def ink(shape, cls):
    """A pencil shape from the sprite (assets/ink.svg), stretched over its box, in the text colour."""
    return f'<svg class="{cls}" aria-hidden="true"><use href="/assets/ink.svg#{shape}"></use></svg>'


def page(lang, title, description, body, path, image=None, noindex=False, current=None):
    """One page; links are from the site root (the site lives at the domain root). `path`: "" or "dictum/".
    `image`: a path from the site root for og:image (the app icon). `noindex`: no canonical / hreflang, kept out of
    search (the activation page, 404). `current`: "updates" marks that nav link as the current page."""
    other = "en" if lang == "ru" else "ru"
    switch = f"/en/{path}" if lang == "ru" else f"/{path}"
    home = "/en/" if lang == "en" else "/"
    url = f"https://{DOMAIN}/{'en/' if lang == 'en' else ''}{path}"
    if noindex:
        seo = '<meta name="robots" content="noindex">'
    else:
        seo = (f'<link rel="canonical" href="{url}">\n'
               f'<link rel="alternate" hreflang="ru" href="https://{DOMAIN}/{path}">\n'
               f'<link rel="alternate" hreflang="en" href="https://{DOMAIN}/en/{path}">\n'
               f'<link rel="alternate" hreflang="x-default" href="https://{DOMAIN}/{path}">\n'
               f'<meta property="og:type" content="website">\n<meta property="og:url" content="{url}">\n'
               f'<meta property="og:title" content="{e(title)}">\n<meta property="og:description" content="{e(description)}">\n'
               f'<meta property="og:locale" content="{"ru_RU" if lang == "ru" else "en_US"}">'
               + (f'\n<meta property="og:image" content="https://{DOMAIN}/{image}">' if image else ""))
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
{seo}
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="/assets/fonts/geist-latin.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/assets/style.css">
<link rel="alternate" type="application/rss+xml" title="{e(T[lang]['rssTitle'])}" href="{home}updates.xml">
<script src="/assets/site.js" defer></script>
</head>
<body>
<div class="wrap">
<header class="top"><a class="brand" href="{home}">kvp projects</a><nav class="nav"><a href="{home}updates/"{' aria-current="page"' if current == "updates" else ""}>{T[lang]['updates']}</a><a class="lang" href="{switch}" hreflang="{other}">{T[lang]['langSwitch']}</a></nav></header>
<main>
{body}
</main>
<footer class="foot"><span>© 2026 {T[lang]['author']}</span><span class="foot-links"><span><a href="{home}updates/">{T[lang]['updates']}</a> · <a href="{home}updates.xml">{T[lang]['rss']}</a></span><a href="{home}privacy/">{T[lang]['privacy']}</a><a class="mail" href="#" data-u="kvp5359" data-d="gmail.com">{T[lang]['contact']}</a></span></footer>
<script>/* The address is put together on click: not in the page for spam bots. */
document.querySelectorAll('a.mail').forEach(a => a.addEventListener('click', e => {{ e.preventDefault(); location.href = 'mailto:' + a.dataset.u + '@' + a.dataset.d; }}));</script>
</div>
</body>
</html>
"""


def actions(p, lang):
    t, out = T[lang], []
    # Dictum and Textum speak only Russian: an English page says so next to the download.
    ui = f' · {t["uiRuOnly"]}' if lang == "en" and "en" not in p.get("ui_langs", ["en", "ru"]) else ""
    for pl in p["platforms"]:
        if pl["kind"] == "mac":
            arch = f' · {pl["arch"]}' if pl.get("arch") else ""   # e.g. "Apple silicon" for arm64-only builds
            v = latest_mac(pl["feed"])
            if v:
                url = f"{RELEASES}/{pl['feed']}-{v}/{urllib.parse.quote(pl['file'])}-{v}.dmg"
                out.append(f'<a class="button" href="{url}">{ink("btn", "frame")}<span>{t["download"]}</span></a>'
                           f'<span class="meta">{t["version"].format(v=v)} · {t["requires"].format(min=pl["min"])}{arch}{ui}</span>')
            else:
                out.append(f'<span class="button is-off">{t["soon"]}</span><span class="meta">{t["requires"].format(min=pl["min"])}{arch}{ui}</span>')
        elif pl["kind"] == "chrome":
            if pl.get("store"):
                out.append(f'<a class="button is-wide" href="{e(pl["store"])}">{ink("btn", "frame")}<span>{t["store"]}</span></a>')
            else:
                out.append(f'<span class="button is-off">{t["chromeSoon"]}</span>')
        else:
            out.append(f'<span class="button is-off">{PLATFORM[pl["kind"]]} — {t["soon"]}</span>')
    return "".join(f'<div class="action">{a}</div>' for a in out)


def changes(p, lang):
    """«What's new» (id="changes"): the newest release open, older ones folded; each release has id="v<version>" — the
    feed and /updates/ link there (assets/site.js unfolds an older one)."""
    t = T[lang]
    released, ru_only = releases(p, lang)
    if not released:
        return ""

    def block(r):
        secs = "".join(f'<h4>{e(s["title"])}</h4><ul>{"".join(f"<li>{inline(i)}</li>" for i in s["items"])}</ul>'
                       for s in r["sections"] if s["items"])
        return (f'<section class="release" id="v{e(r["version"])}"{ru_attr(ru_only)}><h3>{t["version"].format(v=r["version"])}'
                f'<span class="meta"> · {day(r["date"], lang)}</span></h3>{secs}</section>')

    first, rest = released[0], released[1:]
    note = f'<p class="meta">{t["noEn"]}</p>' if ru_only else ""
    older = f'<details><summary>{t["older"]}</summary>{"".join(block(r) for r in rest)}</details>' if rest else ""
    more = (f'<p class="app-updates"><a href="/{"en/" if lang == "en" else ""}updates/#{p["id"]}">{t["appUpdates"].format(name=e(p["name"]))}</a></p>'
            if mac_platform(p) else "")
    return f'<section class="changes" id="changes"><h2>{t["changes"]}</h2>{ink("under", "under")}{note}{block(first)}{older}{more}</section>'


def news(p, lang):
    """The «New in x.y.z» plate under a Mac app's header: the published version's first item, links to #changes."""
    if not mac_platform(p):
        return ""
    released, ru_only = releases(p, lang)
    if not released:
        return ""
    r = released[0]
    return (f'<a class="news" href="#changes"><span class="pulse" aria-hidden="true"></span>'
            f'<b>{T[lang]["newIn"].format(v=e(r["version"]))}</b><span class="news-text"{ru_attr(headline(p, r, lang, ru_only)[1])}>{inline(headline(p, r, lang, ru_only)[0])}</span>'
            f'<span class="news-date">{day(r["date"], lang, short=True)} →</span></a>')


def fresh_badge(p, lang):
    """«Обновлено · x.y.z» next to a Mac app's name: hidden; assets/site.js shows it while the latest PUBLISHED release
    is at most 14 days old (the site is rebuilt only on publish, so the date is checked in the browser). No JS — no badge."""
    if not mac_platform(p):
        return ""
    released, _ = releases(p, lang)
    if not released or not released[0]["date"]:
        return ""
    r = released[0]
    return f' <span class="fresh" data-released="{r["date"]}" hidden>{T[lang]["updated"].format(v=e(r["version"]))}</span>'


def gains(p, lang):
    """«What you get» — three gains {title, text} (content.json `gains`); none (the Chrome extensions) — no section."""
    g = p.get("gains", {}).get(lang)
    if not g:
        return ""
    cells = "".join(f'<div class="gain">{ink("dot", "gain-mark")}<b>{e(x["title"])}</b><span>{e(x["text"])}</span></div>' for x in g)
    return f'<section class="gains"><h2>{T[lang]["gains"]}</h2><div class="gains-grid">{cells}</div></section>'


def updates_page(data, rows, icons, lang):
    """/updates/: all published releases of all Mac apps by date (`rows` — feed()), filter chips (assets/site.js; no JS — all shown)."""
    t, base = T[lang], ("en/" if lang == "en" else "")
    macs = [p for p in data if mac_platform(p)]
    chips = (f'<div class="chips" role="group" aria-label="{t["filter"]}" hidden>'
             f'<button type="button" class="chip" data-app="all" aria-pressed="true">{t["allChip"]}</button>'
             + "".join(f'<button type="button" class="chip" data-app="{p["id"]}" aria-pressed="false">{e(p["name"])}</button>' for p in macs)
             + '</div>')
    html_rows = ""
    for p, r, ru_only in rows:
        its, href = items(r), f'/{base}{p["id"]}/'
        anchor = f'{href}#v{e(r["version"])}'
        more = f'<a class="more" href="{anchor}">{t["more"].format(n=len(its) - 3)}</a>' if len(its) > 3 else ""
        ru = f'<span class="meta"> · {t["inRu"]}</span>' if ru_only else ""
        html_rows += (f'<li class="entry" data-app="{p["id"]}"><img src="/{icons[p["id"]]}" alt="" width="48" height="48">'
                 f'<div class="entry-body"><div class="entry-head"><a class="entry-title" href="{anchor}">{e(p["name"])} {e(r["version"])}</a>'
                 f'<span class="meta">{day(r["date"], lang)}</span>{ru}</div>'
                 f'<ul{ru_attr(ru_only)}>{"".join(f"<li>{inline(i)}</li>" for i in its[:3])}</ul>{more}'
                 f'<a class="entry-link" href="{href}">{t["details"]}</a></div></li>')
    return (f'<section class="hero hero-small"><h1>{t["updates"]}</h1>{ink("under", "under")}<p class="lead">{t["updatesLead"]}</p>'
            f'<p class="subscribe"><a href="/{base}updates.xml">{t["subscribe"]}</a></p></section>'
            f'{chips}<ol class="entries">{html_rows}</ol>')


def rss(rows, lang):
    """/updates.xml (ru), /en/updates.xml (en): RSS 2.0, one item per published release (`rows` — feed()), newest
    first. pubDate — when the version first appeared in its committed feed (feed_history), not the changelog date."""
    t, base = T[lang], ("en/" if lang == "en" else "")
    x = lambda v: html.escape(v, quote=False)
    date = lambda when: email.utils.format_datetime(when)
    # Newest first by that time (a version can reach the feed a day after its changelog date).
    rows = sorted(rows, key=lambda x: x[1].get("published") or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    out = []
    for p, r, ru_only in rows:
        secs = "".join((f'<p><b>{e(s["title"])}</b></p>' if s["title"] else "") + "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in s["items"]) + "</ul>"
                       for s in r["sections"] if s["items"])
        if ru_only:
            secs = f'<p><i>{t["noEn"]}</i></p>' + secs
        link = f'https://{DOMAIN}/{base}{p["id"]}/#v{r["version"]}'
        out.append(f'<item><title>{x(p["name"])} {x(r["version"])}</title><link>{x(link)}</link>'
                   f'<guid isPermaLink="false">{x(p["id"])}-{x(r["version"])}</guid>'
                   + (f'<pubDate>{date(r["published"])}</pubDate>' if r.get("published") else "")
                   + f'<description>{x(secs)}</description></item>')
    # lastBuildDate = the newest release's time in the feed, not the build time: the same file until a new release.
    newest = max((r["published"] for _, r, _ in rows if r.get("published")), default=None)
    self_url = f"https://{DOMAIN}/{base}updates.xml"
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
            f'<title>{x(t["rssTitle"])}</title><link>https://{DOMAIN}/{base}updates/</link><description>{x(t["rssDesc"])}</description>'
            f'<language>{lang}</language><atom:link href="{self_url}" rel="self" type="application/rss+xml"/>'
            + (f'<lastBuildDate>{date(newest)}</lastBuildDate>' if newest else "")
            + "\n" + "\n".join(out) + "\n</channel></rss>\n")


def command(line, lang):
    """The Terminal line for a language: content.json keeps it exactly as in UNINSTALL.md (Russian «Перетащи <App> в
    Корзину вручную» when Finder can't trash the app); an English page prints that message in English."""
    if lang == "ru":
        return line
    out, n = re.subn(r'echo "Перетащи (.+?) в Корзину вручную"', r'echo "Drag \1 to the Trash yourself"', line)
    if n != 1 or re.search("[А-Яа-яЁё]", out):
        sys.exit(f"❌ строка удаления: не нашёл текст для английской страницы: {line[:60]}…")
    return out


def uninstall(p, lang):
    """«How to uninstall»: the in-app way first (mac-app-kit Uninstaller / Note Calc's own), then the Terminal line for
    versions without it. Texts and the line — the Mac platform's `uninstall` in content.json, the line exactly as in
    core/kits/apple-kit/docs/UNINSTALL.md (Note Calc — note-calc/.claude/rules/infrastructure.md)."""
    t = T[lang]
    pl = next((pl for pl in p["platforms"] if pl["kind"] == "mac" and pl.get("uninstall")), None)
    if not pl:
        return ""
    u, name = pl["uninstall"], p["name"]
    published = latest_mac(pl["feed"])
    since = (t["uninstallSince"].format(v=published) if published and num(published) < num(u["since"])
             else t["uninstallFrom"].format(v=u["since"]))
    settings = u.get("settings", {}).get(lang) or t["uninstallSettings"]
    keeps = f' {e(u["keeps"][lang])}' if u.get("keeps") else ""
    note = f' {e(u["manual_note"][lang])}' if u.get("manual_note") else ""
    return (f'<section class="uninstall"><h2>{t["uninstall"]}</h2>'
            f'<p>{e(t["uninstallMenu"].format(name=name, settings=settings))} {e(u["removes"][lang])}{keeps}</p>'
            f'<p>{e(t["uninstallKeep"].format(name=name, label=u.get("keep_label", {}).get(lang) or t["uninstallKeepLabel"]))}</p><p class="meta">{since}</p>'
            f'<details><summary>{t["uninstallManual"]}</summary>'
            f'<p>{e(t["uninstallManualLead"].format(name=name))}{note}</p>'
            f'<div class="cmd"><pre><code>{e(command(u["command"], lang))}</code></pre>'
            f'<button class="copy" type="button" data-done="{t["copiedCmd"]}">{t["copyCmd"]}</button></div></details></section>'
            # Copy the line; without clipboard access the line gets selected for ⌘C.
            '<script>document.querySelectorAll(".cmd .copy").forEach(b => b.addEventListener("click", () => {'
            ' const c = b.parentElement.querySelector("code"), done = () => { b.textContent = b.dataset.done; };'
            ' const select = () => { const r = document.createRange(); r.selectNodeContents(c); getSelection().removeAllRanges(); getSelection().addRange(r); };'
            ' navigator.clipboard ? navigator.clipboard.writeText(c.textContent).then(done, select) : select(); }));</script>')


def merge_registry(data):
    """Identity fields come from the kvp registry (core/spec/products.json): per site platform the feed, file name,
    link scheme, minimum macOS and «Apple silicon» for arm64-only builds; per product the changelogs (in the platform
    folder) and the icon (in the product's brand/). content.json keeps only what is written for people."""
    sys.path.insert(0, os.path.join(ROOT, "..", "release", "shared"))
    import registry
    reg = registry.load()
    for p in data:
        rp = reg[p["id"]]
        root = registry.product_root(p["id"], rp)
        for pl in p["platforms"]:
            name, rpl = next((n, x) for n, x in rp["platforms"].items() if x.get("site") == pl["kind"])
            for key in ("feed", "file", "scheme"):
                if rpl.get(key):
                    pl[key] = rpl[key]
            if rpl.get("minOS"):
                pl["min"] = f"macOS {rpl['minOS']}"
            if rpl.get("arch") == ["arm64"]:
                pl["arch"] = "Apple silicon"
            folder = os.path.join(root, rpl["dir"])
            if "changelog" not in p:
                p["changelog"] = os.path.join(folder, "CHANGELOG.md")
                if os.path.exists(os.path.join(folder, "CHANGELOG.en.md")):
                    p["changelog_en"] = os.path.join(folder, "CHANGELOG.en.md")
        if rp.get("icon"):
            icon = p.setdefault("icon", {})
            icon["fallback" if "icns" in icon else "png"] = os.path.join(root, rp["icon"])
    return data


def build():
    data = merge_registry(json.load(open(os.path.join(ROOT, "content.json"), encoding="utf-8"))["products"])
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets", "icons"))
    for name in ("style.css", "favicon.svg", "activate.js", "site.js"):
        shutil.copy(os.path.join(ROOT, "assets", name), os.path.join(OUT, "assets"))
    shutil.copytree(os.path.join(ROOT, "assets", "fonts"), os.path.join(OUT, "assets", "fonts"))
    open(os.path.join(OUT, "assets", "ink.svg"), "w").write(pencil.sprite())
    icons = {p["id"]: make_icon(p) for p in data}
    kinds = [k for k in PLATFORM if any(pl["kind"] == k for p in data for pl in p["platforms"])]
    later = [k for k in ("windows", "android", "ios") if k not in kinds]

    for lang in ("ru", "en"):
        t = T[lang]
        base = "en/" if lang == "en" else ""
        sections, n = "", 0
        for kind in kinds:
            title, sub = t["sections"][kind]
            cards = ""
            for p in (p for p in data if any(pl["kind"] == kind for pl in p["platforms"])):
                # The name leads; under it — what the app gives you (`benefit`), not what it is.
                cards += (f'<a class="card" href="/{base}{p["id"]}/">{ink("card1" if n % 2 == 0 else "card2", "frame")}'
                          f'<img src="/{icons[p["id"]]}" alt="" width="72" height="72">'
                          f'<span class="card-text"><span class="card-head"><b>{e(p["name"])}</b>{beta(p, lang)}{fresh_badge(p, lang)}</span>'
                          f'<span class="benefit">{e(p["benefit"][lang])}</span></span></a>')
                n += 1
            sections += (f'<section class="group" id="{kind}"><div class="group-head"><h2>{title}</h2>'
                         f'<span class="meta">{sub}</span></div><div class="grid">{cards}</div></section>')
        nxt = f'<p class="meta next">{t["next"].format(list=", ".join(PLATFORM[k] for k in later))}</p>' if later else ""
        # «Latest updates»: the newest published release of each Mac app, the three most recent (one line per app — a
        # busy app doesn't push the others out).
        rows, seen, latest = feed(data, lang), set(), []
        for x in rows:
            if x[0]["id"] not in seen:
                seen.add(x[0]["id"])
                latest.append(x)
        fresh = "".join(f'<li><a class="feed-row" href="/{base}{p["id"]}/#v{e(r["version"])}"><img src="/{icons[p["id"]]}" alt="" width="32" height="32">'
                        f'<b>{e(p["name"])} {e(r["version"])}</b><span class="feed-text"{ru_attr(headline(p, r, lang, ru)[1])}>{inline(headline(p, r, lang, ru)[0])}</span>'
                        f'<span class="feed-date">{day(r["date"], lang, short=True)}</span></a></li>' for p, r, ru in latest[:3])
        fresh = (f'<section class="fresh-box" aria-labelledby="fresh"><div class="fresh-head"><h2 id="fresh">{t["fresh"]}</h2>'
                 f'<a href="/{base}updates/">{t["allUpdates"]}</a></div><ul>{fresh}</ul></section>') if fresh else ""
        body = f'<section class="hero"><h1>{t["h1"]}</h1>{ink("under", "under")}<p class="lead">{t["lead"]}</p></section>{fresh}{sections}{nxt}'
        write(base + "index.html", page(lang, t["title"], t["lead"], body, ""))
        write(base + "updates/index.html", page(lang, f'{t["updates"]} — kvp projects', t["updatesLead"], updates_page(data, rows, icons, lang),
                                                "updates/", current="updates"))
        write(base + "updates.xml", rss(rows, lang))

        for p in data:
            feats = "".join(f'<li>{ink("dot", "dot")}<span>{e(f)}</span></li>' for f in p["features"][lang])
            body = (f'<a class="back" href="/{base}">← {t["all"]}</a>'
                    f'<section class="product"><img src="/{icons[p["id"]]}" alt="" width="144" height="144">'
                    f'<div class="product-head"><h1>{e(p["name"])}{beta(p, lang)}</h1><p class="lead benefit-lead">{e(p["benefit"][lang])}</p></div></section>'
                    f'{news(p, lang)}<p class="summary">{e(p["summary"][lang])}</p><div class="actions">{actions(p, lang)}</div>'
                    f'{beta_note(p, lang)}{gains(p, lang)}'
                    f'<section class="features"><h2>{t["features"]}</h2><ul>{feats}</ul></section>{changes(p, lang)}{uninstall(p, lang)}')
            write(f'{base}{p["id"]}/index.html', page(lang, f'{p["name"]} — {p["tagline"][lang]}', p["summary"][lang], body, p["id"] + "/", image=icons[p["id"]]))

    # The license activation page: the purchase email links here (license-tool issue prints the link); the key is in
    # the fragment (#key=…), which browsers never send to the server. assets/activate.js does the rest.
    for lang in ("ru", "en"):
        t = T[lang]
        base = "en/" if lang == "en" else ""
        apps = [{"id": p["id"], "name": p["name"], "scheme": pl["scheme"], "page": f"/{base}{p['id']}/",
                 "path": pl.get("license_path", {}).get(lang, "")}
                for p in data for pl in p["platforms"] if pl.get("scheme")]
        texts = {k: t[k] for k in ("openIn", "noKey", "copied", "copyManually", "unknownApp", "paste")}
        texts["download"] = t["downloadApp"]
        payload = json.dumps({"apps": apps, "texts": texts}, ensure_ascii=False).replace("</", "<\\/")
        body = (f'<section class="hero"><h1>{t["activateTitle"]}</h1>{ink("under", "under")}<p class="lead">{t["activateLead"]}</p></section>'
                f'<div class="actions" id="open"></div><p class="key-line"><code id="key"></code></p>'
                f'<div class="action"><button class="button" id="copy" type="button">{ink("btn", "frame")}<span>{t["copy"]}</span></button></div>'
                f'<script type="application/json" id="activate-data">{payload}</script><script src="/assets/activate.js"></script>')
        write(f"{base}activate/index.html", page(lang, t["activateTitle"], t["activateLead"], body, "activate/", noindex=True))

    # The privacy page: what leaves the Mac and why (PRIVACY above), linked from every footer.
    for lang in ("ru", "en"):
        pv, base = PRIVACY[lang], ("en/" if lang == "en" else "")
        contact = f'<a class="mail" href="#" data-u="kvp5359" data-d="gmail.com">{pv["contact"]}</a>'
        secs = "".join(f'<h2>{e(h)}</h2>' + "".join(f'<p>{x.replace("{contact}", contact)}</p>' for x in paras)
                       for h, paras in pv["sections"])
        body = (f'<section class="hero"><h1>{pv["title"]}</h1>{ink("under", "under")}<p class="lead">{pv["lead"]}</p></section>'
                f'<section class="prose">{secs}</section>')
        write(f"{base}privacy/index.html", page(lang, f'{pv["title"]} — kvp projects', pv["lead"], body, "privacy/"))

    write("404.html", page("ru", T["ru"]["notFound"], "", f'<section class="hero"><h1>{T["ru"]["notFound"]}</h1>'
                           f'<p class="lead"><a href="/">{T["ru"]["home"]}</a> · <a href="/en/">Home</a></p></section>', "", noindex=True))
    # Search engines: every indexable page in both languages (not /activate/ and 404 — they are noindex).
    paths = [""] + [p["id"] + "/" for p in data] + ["updates/", "privacy/"]
    urls = "".join(f"<url><loc>https://{DOMAIN}/{pre}{path}</loc></url>\n" for path in paths for pre in ("", "en/"))
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: https://{DOMAIN}/sitemap.xml\n")
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    print(f"✅ {DOMAIN}: {len(data)} продуктов → docs/")


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    build()
