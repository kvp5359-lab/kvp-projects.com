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
RELEASES = "https://github.com/kvp5359-lab/updates/releases/download"
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
        "sections": {"mac": ("For Mac", "macOS"), "chrome": ("For the browser", "Google Chrome"), "windows": ("For Windows", ""),
                     "linux": ("For Linux", ""), "ios": ("For iPhone and iPad", "iOS"), "android": ("For Android", "")},
    },
}
PLATFORM = {"mac": "macOS", "chrome": "Chrome", "windows": "Windows", "linux": "Linux", "ios": "iOS", "android": "Android"}

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
    """The newest version in the app's update feed (../updates/<feed>/appcast.xml), or None before the first release."""
    path = os.path.join(ROOT, "..", "updates", feed, "appcast.xml")
    tauri = os.path.join(ROOT, "..", "updates", feed, "latest.json")   # note-calc: Tauri's updater feed
    if os.path.exists(tauri):
        return json.load(open(tauri, encoding="utf-8")).get("version")
    if not os.path.exists(path):
        return None
    items = ET.parse(path).getroot().findall("./channel/item")
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


def page(lang, title, description, body, path):
    """One page; links are from the site root (the site lives at the domain root). `path`: "" or "dictum/"."""
    other = "en" if lang == "ru" else "ru"
    switch = f"/en/{path}" if lang == "ru" else f"/{path}"
    home = "/en/" if lang == "en" else "/"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="alternate" hreflang="ru" href="https://{DOMAIN}/{path}">
<link rel="alternate" hreflang="en" href="https://{DOMAIN}/en/{path}">
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
<footer class="foot"><span>© 2026 {T[lang]['author']}</span><a class="mail" href="#" data-u="kvp5359" data-d="gmail.com">{T[lang]['contact']}</a></footer>
<script>/* The address is put together on click: not in the page for spam bots. */
document.querySelectorAll('a.mail').forEach(a => a.addEventListener('click', e => {{ e.preventDefault(); location.href = 'mailto:' + a.dataset.u + '@' + a.dataset.d; }}));</script>
</div>
</body>
</html>
"""


def actions(p, lang):
    t, out = T[lang], []
    for pl in p["platforms"]:
        if pl["kind"] == "mac":
            v = latest_mac(pl["feed"])
            if v:
                url = f"{RELEASES}/{pl['feed']}-{v}/{urllib.parse.quote(pl['file'])}-{v}.dmg"
                out.append(f'<a class="button" href="{url}">{ink("btn", "frame")}<span>{t["download"]}</span></a>'
                           f'<span class="meta">{t["version"].format(v=v)} · {t["requires"].format(min=pl["min"])}</span>')
            else:
                out.append(f'<span class="button is-off">{t["soon"]}</span><span class="meta">{t["requires"].format(min=pl["min"])}</span>')
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
    for name in ("style.css", "favicon.svg"):
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
            write(f'{base}{p["id"]}/index.html', page(lang, f'{p["name"]} — {p["tagline"][lang]}', p["summary"][lang], body, p["id"] + "/"))

    write("404.html", page("ru", T["ru"]["notFound"], "", f'<section class="hero"><h1>{T["ru"]["notFound"]}</h1>'
                           f'<p class="lead"><a href="/">{T["ru"]["home"]}</a> · <a href="/en/">Home</a></p></section>', ""))
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    print(f"✅ {DOMAIN}: {len(data)} продуктов → docs/")


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    build()
