#!/usr/bin/env python3
"""Builds kvp-projects.com into docs/ (GitHub Pages serves that folder).

Reads products.json, each product's CHANGELOG.md (and CHANGELOG.en.md when it has one) and the update feeds in
../updates (the newest released version → the download link). Run after a release or a change in products.json:
    python3 build.py
Paths in products.json are relative to this folder; the shelf ~/Проекты/mac-apps must be next to it.
"""
import html, json, os, re, shutil, subprocess, sys, urllib.parse
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
DOMAIN = "kvp-projects.com"
RELEASES = "https://github.com/kvp5359-lab/updates/releases/download"
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"

T = {
    "ru": {
        "title": "kvp projects", "lead": "Небольшие программы, которые я делаю для себя и делюсь ими. Mac-приложения и расширения для Chrome — дальше Windows, Android и iOS.",
        "apps": "Приложения", "download": "Скачать для Mac", "soon": "Скоро", "store": "Установить из Chrome Web Store",
        "chromeSoon": "Скоро в Chrome Web Store", "requires": "Нужна {min} или новее", "chromeReq": "Google Chrome и браузеры на его основе",
        "version": "Версия {v}", "changes": "Что нового", "older": "Предыдущие версии", "all": "Все программы",
        "free": "Бесплатно. Тексты, записи и файлы остаются у тебя.", "noEn": "", "langSwitch": "English", "unreleased": "Готовится",
        "notFound": "Такой страницы нет", "home": "На главную",
    },
    "en": {
        "title": "kvp projects", "lead": "Small apps I make for myself and share. Mac apps and Chrome extensions — Windows, Android and iOS are next.",
        "apps": "Apps", "download": "Download for Mac", "soon": "Coming soon", "store": "Add from Chrome Web Store",
        "chromeSoon": "Coming soon to Chrome Web Store", "requires": "Requires {min} or later", "chromeReq": "Google Chrome and Chromium-based browsers",
        "version": "Version {v}", "changes": "What’s new", "older": "Earlier versions", "all": "All apps",
        "free": "Free. Your texts, recordings and files stay with you.", "noEn": "The change history is available in Russian.", "langSwitch": "Русский", "unreleased": "In the works",
        "notFound": "Page not found", "home": "Home",
    },
}
PLATFORM = {"mac": "macOS", "chrome": "Chrome", "windows": "Windows", "linux": "Linux", "ios": "iOS", "android": "Android"}
CAMERA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4aa3ff"/><stop offset="1" stop-color="#0a64e0"/></linearGradient></defs><rect x="16" y="16" width="224" height="224" rx="52" fill="url(#g)"/><g fill="none" stroke="#fff" stroke-width="14" stroke-linecap="round"><path d="M64 96V76a12 12 0 0 1 12-12h20M160 64h20a12 12 0 0 1 12 12v20M192 160v20a12 12 0 0 1-12 12h-20M96 192H76a12 12 0 0 1-12-12v-20"/><circle cx="128" cy="128" r="30"/></g></svg>"""

e = html.escape


def rel(p):
    return p if os.path.isabs(p) else os.path.normpath(os.path.join(ROOT, p))


def parse_changelog(path):
    """Keep a Changelog, the shelf's rules: [(version|None, date, [(section, [items])])], newest first."""
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
    if not os.path.exists(path):
        return None
    items = ET.parse(path).getroot().findall("./channel/item")
    versions = [i.findtext(SPARKLE + "shortVersionString") for i in items]
    versions = [v for v in versions if v]
    return max(versions, key=lambda v: [int(x) for x in v.split(".")]) if versions else None


def make_icon(p):
    dest = os.path.join(OUT, "assets", "icons", p["id"] + (".svg" if "symbol" in p["icon"] else ".png"))
    icon = p["icon"]
    if "symbol" in icon:
        open(dest, "w").write(CAMERA_SVG)
    else:
        src = next((rel(icon[k]) for k in ("icns", "fallback", "png") if icon.get(k) and os.path.exists(rel(icon[k]))), None)
        if not src:
            sys.exit(f"❌ нет значка для {p['id']}")
        subprocess.run(["sips", "-s", "format", "png", "--resampleHeightWidthMax", "256", src, "--out", dest],
                       check=True, capture_output=True)
    return "assets/icons/" + os.path.basename(dest)


def page(lang, title, description, body, path):
    """One page; links are from the site root (the site lives at the domain root). `path`: "" or "dictum/"."""
    other = "en" if lang == "ru" else "ru"
    switch = f"/en/{path}" if lang == "ru" else f"/{path}"
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
<link rel="stylesheet" href="/assets/style.css">
</head>
<body>
<header class="top"><a class="brand" href="/{'en/' if lang == 'en' else ''}">kvp projects</a><a class="lang" href="{switch}" hreflang="{other}">{T[lang]['langSwitch']}</a></header>
<main>
{body}
</main>
<footer class="foot">© 2026 Kirill Prudnikov · <a href="mailto:kvp5359@gmail.com">kvp5359@gmail.com</a></footer>
</body>
</html>
"""


def platform_badges(p):
    return "".join(f'<span class="badge">{PLATFORM[x["kind"]]}</span>' for x in p["platforms"])


def actions(p, lang):
    t, out = T[lang], []
    for pl in p["platforms"]:
        if pl["kind"] == "mac":
            v = latest_mac(pl["feed"])
            if v:
                url = f"{RELEASES}/{pl['feed']}-{v}/{urllib.parse.quote(pl['file'])}-{v}.dmg"
                out.append(f'<a class="button" href="{url}">{t["download"]}</a><span class="meta">{t["version"].format(v=v)} · {t["requires"].format(min=pl["min"])}</span>')
            else:
                out.append(f'<span class="button is-off">{t["soon"]}</span><span class="meta">{t["requires"].format(min=pl["min"])}</span>')
        elif pl["kind"] == "chrome":
            if pl.get("store"):
                out.append(f'<a class="button" href="{e(pl["store"])}">{t["store"]}</a><span class="meta">{t["chromeReq"]}</span>')
            else:
                out.append(f'<span class="button is-off">{t["chromeSoon"]}</span><span class="meta">{t["chromeReq"]}</span>')
        else:
            out.append(f'<span class="button is-off">{PLATFORM[pl["kind"]]} — {t["soon"]}</span>')
    return "".join(f'<div class="action">{a}</div>' for a in out)


def changes(p, lang):
    t = T[lang]
    log = parse_changelog(p.get("changelog_en")) if lang == "en" else parse_changelog(p.get("changelog"))
    if log is None:
        return f'<p class="meta">{t["noEn"]}</p>' if lang == "en" and t["noEn"] else ""
    released = [r for r in log if r["version"]]
    if not released:
        return ""

    def block(r):
        secs = "".join(f'<h4>{e(s["title"])}</h4><ul>{"".join(f"<li>{inline(i)}</li>" for i in s["items"])}</ul>' for s in r["sections"] if s["items"])
        return f'<section class="release"><h3>{t["version"].format(v=r["version"])}<span class="meta"> · {r["date"] or ""}</span></h3>{secs}</section>'

    first, rest = released[0], released[1:]
    older = f'<details><summary>{t["older"]}</summary>{"".join(block(r) for r in rest)}</details>' if rest else ""
    return f'<h2>{t["changes"]}</h2>{block(first)}{older}'


def build():
    data = json.load(open(os.path.join(ROOT, "products.json"), encoding="utf-8"))["products"]
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, "assets", "icons"))
    shutil.copy(os.path.join(ROOT, "assets", "style.css"), os.path.join(OUT, "assets"))
    shutil.copy(os.path.join(ROOT, "assets", "favicon.svg"), os.path.join(OUT, "assets"))
    icons = {p["id"]: make_icon(p) for p in data}

    for lang in ("ru", "en"):
        t = T[lang]
        base = "en/" if lang == "en" else ""
        cards = "".join(
            f'<a class="card" href="/{base}{p["id"]}/"><img src="/{icons[p["id"]]}" alt="" width="64" height="64">'
            f'<div><h3>{e(p["name"])}</h3><p>{e(p["tagline"][lang])}</p><div class="badges">{platform_badges(p)}</div></div></a>'
            for p in data)
        body = f'<section class="hero"><h1>{t["title"]}</h1><p class="lead">{t["lead"]}</p></section><h2>{t["apps"]}</h2><div class="grid">{cards}</div>'
        write(base + "index.html", page(lang, t["title"], t["lead"], body, ""))

        for p in data:
            feats = "".join(f"<li>{e(f)}</li>" for f in p["features"][lang])
            body = (f'<a class="back" href="/{base}">← {t["all"]}</a>'
                    f'<section class="product"><img src="/{icons[p["id"]]}" alt="" width="128" height="128">'
                    f'<div><h1>{e(p["name"])}</h1><p class="lead">{e(p["tagline"][lang])}</p><div class="badges">{platform_badges(p)}</div></div></section>'
                    f'<p>{e(p["summary"][lang])}</p><div class="actions">{actions(p, lang)}</div>'
                    f'<ul class="features">{feats}</ul><p class="meta">{t["free"]}</p>{changes(p, lang)}')
            write(f'{base}{p["id"]}/index.html',
                  page(lang, f'{p["name"]} — {p["tagline"][lang]}', p["summary"][lang], body, p["id"] + "/"))

    write("404.html", page("ru", T["ru"]["notFound"], "", f'<section class="hero"><h1>{T["ru"]["notFound"]}</h1><p><a href="/">{T["ru"]["home"]}</a> · <a href="/en/">Home</a></p></section>', ""))
    write("CNAME", DOMAIN + "\n")
    write(".nojekyll", "")
    print(f"✅ {DOMAIN}: {len(data)} продуктов → docs/")


def write(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    build()
