#!/usr/bin/env python3
"""Builds kvp-projects.com into docs/ (GitHub Pages serves that folder).

Reads products.json, each product's CHANGELOG.md (and CHANGELOG.en.md when it has one) and the update feeds in
../updates (the newest released version → the download link). Run after a release or a change in products.json:
    python3 build.py
Paths in products.json are relative to this folder; the shelf ~/Проекты/mac-apps must be next to it.
The look — the design on claude.ai (canvas «kvp-projects.com»): white paper, dark ink, pencil frames drawn like
Dictum's pencil style (pencil.py).
"""
import html, json, os, re, shutil, subprocess, sys, urllib.parse
import xml.etree.ElementTree as ET

import pencil

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
DOMAIN = "kvp-projects.com"
RELEASES = "https://updates.kvp-projects.com/files"   # our server (docs/updates-server.md); GitHub Releases is the archive
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"

T = {
    "ru": {
        "title": "kvp projects", "h1": "Приложения для Mac<br>и браузера",
        "lead": "Диктовка, работа с текстом, буфер обмена, скриншоты, заметки-калькулятор и расширения для Chrome.",
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
        "sections": {"mac": ("Для Mac", "macOS"), "chrome": ("Для браузера", "Google Chrome"), "windows": ("Для Windows", ""),
                     "linux": ("Для Linux", ""), "ios": ("Для iPhone и iPad", "iOS"), "android": ("Для Android", "")},
    },
    "en": {
        "title": "kvp projects", "h1": "Apps for Mac<br>and the browser",
        "lead": "Dictation, text tools, clipboard history, screenshots, a calculator notepad and Chrome extensions.",
        "download": "Download for Mac", "soon": "Coming soon", "store": "Add from Chrome Web Store",
        "chromeSoon": "Coming soon to Chrome Web Store", "requires": "{min} or later",
        "beta": "Beta", "betaNote": "Beta: the app is in active development, more is on the way.",
        "version": "Version {v}", "features": "Features", "changes": "What’s new", "older": "Earlier versions",
        "all": "All apps", "noEn": "The change history is available in Russian.", "langSwitch": "Русский",
        "next": "Coming next: {list}.", "notFound": "Page not found", "home": "Home", "author": "Kirill Prudnikov", "contact": "Contact me",
        "activateTitle": "License activation", "activateLead": "Press the button — the app opens and the key goes in by itself. If the app isn’t on this Mac, download it and press the button again, or copy the key and paste it yourself.",
        "openIn": "Open {name}", "copy": "Copy Key", "copied": "Copied", "copyManually": "The key is selected — press ⌘C",
        "noKey": "There’s no key in this link, or it’s damaged — open the link from the email again.",
        "unknownApp": "This link points to an app I don’t know. Choose your app below.",
        "paste": "By hand: {path}", "downloadApp": "{name} page",
        "uiRuOnly": "Interface: Russian only", "privacy": "Privacy",
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
                "Раз в день приложение проверяет, нет ли новой версии, и читает файл с правилами лицензий на updates.kvp-projects.com. Это обычное скачивание файла: о тебе и о том, как ты пользуешься приложением, ничего не отправляется. Как и любой сайт, сервер видит адрес, с которого пришёл запрос. Новая версия ставится только с твоего согласия, автоматическую проверку можно выключить в настройках. Сами файлы приложений скачиваются с GitHub.",
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
                "Once a day an app checks for a new version and reads the license policy file on updates.kvp-projects.com. It’s a plain file download: nothing about you or how you use the app is sent. Like any website, the server sees the address the request came from. A new version is installed only with your consent, and automatic checks can be turned off in settings. The app files themselves are downloaded from GitHub.",
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


def latest_mac(feed):
    """The newest PUBLISHED version in the app's update feed: ../updates/<feed>/appcast.xml (or note-calc's latest.json)
    as committed in the updates repo (HEAD), not the working tree — release.sh writes feeds there before publish.sh
    uploads the files, and the site must never link to a download that isn't on GitHub yet. None before the first release."""
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
    """The «Бета» mark: every product until products.json says "beta": false (a 1.0 release)."""
    return f' <span class="beta">{T[lang]["beta"]}</span>' if p.get("beta", True) else ""


def beta_note(p, lang):
    return f'<p class="meta beta-note">{T[lang]["betaNote"]}</p>' if p.get("beta", True) else ""


def ink(shape, cls):
    """A pencil shape from the sprite (assets/ink.svg), stretched over its box, in the text colour."""
    return f'<svg class="{cls}" aria-hidden="true"><use href="/assets/ink.svg#{shape}"></use></svg>'


def page(lang, title, description, body, path, image=None, noindex=False):
    """One page; links are from the site root (the site lives at the domain root). `path`: "" or "dictum/".
    `image`: a path from the site root for og:image (the app icon). `noindex`: no canonical / hreflang, kept out of
    search (the activation page, 404)."""
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
</head>
<body>
<div class="wrap">
<header class="top"><a class="brand" href="{home}">kvp projects</a><a class="lang" href="{switch}" hreflang="{other}">{T[lang]['langSwitch']}</a></header>
<main>
{body}
</main>
<footer class="foot"><span>© 2026 {T[lang]['author']}</span><span class="foot-links"><a href="{home}privacy/">{T[lang]['privacy']}</a><a class="mail" href="#" data-u="kvp5359" data-d="gmail.com">{T[lang]['contact']}</a></span></footer>
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
    t = T[lang]
    log = parse_changelog(p.get("changelog_en")) if lang == "en" else parse_changelog(p.get("changelog"))
    if log is None:
        return f'<p class="meta">{t["noEn"]}</p>' if t["noEn"] else ""
    released = [r for r in log if r["version"]]
    # Never ahead of the Download button: a Mac app shows only versions already published in its feed.
    feeds = [pl["feed"] for pl in p.get("platforms", []) if pl["kind"] == "mac"]
    if feeds:
        published = latest_mac(feeds[0])
        num = lambda v: [int(x) for x in v.split(".")]
        released = [r for r in released if published and num(r["version"]) <= num(published)]
    if not released:
        return ""

    def block(r):
        secs = "".join(f'<h4>{e(s["title"])}</h4><ul>{"".join(f"<li>{inline(i)}</li>" for i in s["items"])}</ul>'
                       for s in r["sections"] if s["items"])
        return f'<section class="release"><h3>{t["version"].format(v=r["version"])}<span class="meta"> · {r["date"] or ""}</span></h3>{secs}</section>'

    first, rest = released[0], released[1:]
    older = f'<details><summary>{t["older"]}</summary>{"".join(block(r) for r in rest)}</details>' if rest else ""
    return f'<section class="changes"><h2>{t["changes"]}</h2>{ink("under", "under")}{block(first)}{older}</section>'


def build():
    data = json.load(open(os.path.join(ROOT, "products.json"), encoding="utf-8"))["products"]
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets", "icons"))
    for name in ("style.css", "favicon.svg", "activate.js"):
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
                cards += (f'<a class="card" href="/{base}{p["id"]}/">{ink("card1" if n % 2 == 0 else "card2", "frame")}'
                          f'<img src="/{icons[p["id"]]}" alt="" width="72" height="72">'
                          f'<span class="card-text"><b>{e(p["name"])}{beta(p, lang)}</b><span>{e(p["tagline"][lang])}</span></span></a>')
                n += 1
            sections += (f'<section class="group" id="{kind}"><div class="group-head"><h2>{title}</h2>'
                         f'<span class="meta">{sub}</span></div><div class="grid">{cards}</div></section>')
        nxt = f'<p class="meta next">{t["next"].format(list=", ".join(PLATFORM[k] for k in later))}</p>' if later else ""
        body = f'<section class="hero"><h1>{t["h1"]}</h1>{ink("under", "under")}<p class="lead">{t["lead"]}</p></section>{sections}{nxt}'
        write(base + "index.html", page(lang, t["title"], t["lead"], body, ""))

        for p in data:
            feats = "".join(f'<li>{ink("dot", "dot")}<span>{e(f)}</span></li>' for f in p["features"][lang])
            body = (f'<a class="back" href="/{base}">← {t["all"]}</a>'
                    f'<section class="product"><img src="/{icons[p["id"]]}" alt="" width="144" height="144">'
                    f'<div><h1>{e(p["name"])}{beta(p, lang)}</h1><p class="lead">{e(p["tagline"][lang])}</p></div></section>'
                    f'<p class="summary">{e(p["summary"][lang])}</p><div class="actions">{actions(p, lang)}</div>'
                    f'{beta_note(p, lang)}'
                    f'<section class="features"><h2>{t["features"]}</h2><ul>{feats}</ul></section>{changes(p, lang)}')
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
    paths = [""] + [p["id"] + "/" for p in data] + ["privacy/"]
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
