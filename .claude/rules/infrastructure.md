# Инфраструктура kvp-projects.com

## Стек
Статический сайт без фреймворков: `build.py` (Python 3, только стандартная библиотека + `sips` macOS для значков)
собирает HTML из `products.json`, журналов изменений продуктов и лент обновлений. Оформление — `assets/style.css`
(белая «бумага», тёмные «чернила», шрифт Geist лежит на самом сайте (`assets/fonts`, без обращений к Google — адреса посетителей не уходят третьим лицам); тёмная тема по системе). Рамки, кнопка, точки списка и
подчёркивания — карандашные линии: `pencil.py` (порт карандаша Dictum, `transcribe-app/…/Overlay/Styles/Pencil`)
рисует их в `docs/assets/ink.svg`, страницы берут их через `<use>`; цвет — цвет текста. Макет — холст Claude Design
«kvp-projects.com» (https://claude.ai/artifact/V7xFSSXVpojr8stdtuZFAY).

## Архитектура
- `products.json` — каталог. Продукт: `id` (адрес страницы), `name`, `icon` (`icns` установленного приложения →
  запасной `fallback`, `png`, или `symbol` — нарисованный значок), `changelog` / `changelog_en`, тексты `tagline`,
  `summary`, `features` на `ru`/`en`, `platforms`: `{kind: mac, min, feed, file}` / `{kind: chrome, store}` / позже
  `windows`, `linux`, `ios`, `android`. Новая платформа у продукта = ещё одна запись в `platforms`.
- Кнопка «Скачать для Mac» появляется сама, когда в ленте `../updates/<feed>/appcast.xml` (у note-calc — `latest.json`) есть выпуск: ссылка
  `https://github.com/kvp5359-lab/updates/releases/download/<feed>-<версия>/<file>-<версия>.dmg` (так называет файлы
  `distribution/scripts/release.sh`). До выпуска — «Скоро». У расширений — ссылка `store` или «Скоро в Chrome Web Store».
- Главная — разделы по платформам (Mac, браузер, дальше Windows / Android / iOS — появляются сами, когда у продукта есть
  такая платформа; пока их нет — строка «Скоро — …»).
- Пометка «Бета» у каждого продукта (карточка, заголовок, строка под кнопкой) — пока в `products.json` у него нет
  `"beta": false` (поставить при выпуске 1.0). О цене на сайте не пишем (решение пользователя).
- «Что нового» — последняя версия из журнала, остальные свёрнуты. Английская страница берёт `changelog_en`; если его нет —
  строка «история изменений — на русском».
- Пути в `products.json` — относительно этой папки: соседи по полке `../<приложение>`, расширения `../../chrome-extentions/…`.

## Деплой
- Публичный репозиторий GitHub `kvp5359-lab/kvp-projects.com`, GitHub Pages из папки `docs/` ветки `main`, свой домен
  `kvp-projects.com` (файл `docs/CNAME`). DNS — на Hostinger: A-записи корня на адреса GitHub Pages, `www` — CNAME на
  `kvp5359-lab.github.io`.
- Обновить сайт: `python3 build.py` → коммит → `git push` (только с «да» пользователя).
- Ленты обновлений живут отдельно (`../updates`, `updates.kvp-projects.com/…`) — приложения ходят туда, домен на них не влияет.

## Окружение и секреты
Нет.

## Серверная логика / БД
Нет.

## Локальная разработка
`python3 build.py && python3 -m http.server 8787 -d docs` → http://localhost:8787 (ссылки от корня сайта, поэтому
открывать через сервер, не файлом).
