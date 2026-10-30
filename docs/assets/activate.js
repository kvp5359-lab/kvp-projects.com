// The license activation page (kvp-projects.com/activate/#app=dictum&key=KVP1.…): a button opens the app through its
// URL scheme — <scheme>://activate?key=… — and the key goes in by itself; or the key is shown to copy. The key lives in
// the fragment (never sent to a server); after reading it the page drops it from the address bar and keeps it in memory.
// No automatic opening: a browser without the app shows an error page or an alert for an unknown scheme.
(() => {
  addEventListener("hashchange", () => location.reload());   // another link pasted into this tab
  const data = JSON.parse(document.getElementById("activate-data").textContent);
  const t = data.texts;
  const params = new URLSearchParams(location.hash.slice(1));
  const raw = params.get("key") || "", appId = params.get("app") || "";
  const key = raw.length <= 2048 && /^KVP1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(raw) ? raw : "";
  const open = document.getElementById("open"), copy = document.getElementById("copy"), keyLine = document.getElementById("key");

  // The language switch keeps the key (the link stays on this page); then the key leaves the URL and the history.
  const lang = document.querySelector("a.lang");
  if (lang && location.hash) lang.href = lang.getAttribute("href") + location.hash;
  if (location.hash) {
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) { /* stays in the URL */ }
  }

  const note = (text) => {
    const p = document.createElement("p");
    p.className = "meta";
    p.textContent = text;
    open.append(p);
  };
  if (!key) {
    note(t.noKey);
    copy.parentElement.remove();
    keyLine.parentElement.remove();
    return;
  }
  keyLine.textContent = key;

  const target = data.apps.find((a) => a.id === appId);
  if (appId && !target) note(t.unknownApp);
  for (const a of target ? [target] : data.apps) {
    const l = document.createElement("a");
    l.className = "button";
    l.href = a.scheme + "://activate?key=" + encodeURIComponent(key);
    l.innerHTML = '<svg class="frame" aria-hidden="true"><use href="/assets/ink.svg#btn"></use></svg><span></span>';
    l.querySelector("span").textContent = t.openIn.replace("{name}", a.name);
    const hint = document.createElement("span");
    hint.className = "meta";
    if (a.path) hint.textContent = t.paste.replace("{path}", a.path) + " · ";
    const page = document.createElement("a");
    page.href = a.page;
    page.textContent = t.download.replace("{name}", a.name);
    hint.append(page);
    const row = document.createElement("div");
    row.className = "action";
    row.append(l, hint);
    open.append(row);
  }

  copy.onclick = () => {
    const done = () => { copy.querySelector("span").textContent = t.copied; };
    const manual = () => {   // no clipboard access: select the key so ⌘C / Ctrl+C works
      const r = document.createRange();
      r.selectNodeContents(keyLine);
      const s = getSelection();
      s.removeAllRanges();
      s.addRange(r);
      const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
      copy.querySelector("span").textContent = t.copyManually.replace("{shortcut}", mac ? "⌘C" : "Ctrl+C");
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(key).then(done).catch(manual);
    else manual();
  };
})();
