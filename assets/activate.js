// The license activation page (kvp-projects.com/activate/#app=dictum&key=KVP1.…): opens the app through its URL
// scheme — the key goes in by itself — or shows the key to copy. The key stays in the fragment: never sent anywhere.
(() => {
  const data = JSON.parse(document.getElementById("activate-data").textContent);
  const params = new URLSearchParams(location.hash.slice(1));
  const key = params.get("key") || "", app = params.get("app");
  const open = document.getElementById("open"), copy = document.getElementById("copy");
  if (!key) {
    open.innerHTML = '<p class="meta"></p>';
    open.firstChild.textContent = data.texts.noKey;
    copy.remove();
    return;
  }
  document.getElementById("key").textContent = key;
  const link = (a) => a.scheme + "://activate?key=" + encodeURIComponent(key);
  for (const a of data.apps.filter((a) => !app || a.id === app)) {
    const l = document.createElement("a");
    l.className = "button";
    l.href = link(a);
    l.innerHTML = '<svg class="frame" aria-hidden="true"><use href="/assets/ink.svg#btn"></use></svg><span></span>';
    l.querySelector("span").textContent = data.texts.openIn.replace("{name}", a.name);
    const row = document.createElement("div");
    row.className = "action";
    row.append(l);
    open.append(row);
  }
  const target = data.apps.find((a) => a.id === app);
  if (target) location.href = link(target);   // one app: try it right away
  copy.onclick = () => navigator.clipboard.writeText(key).then(() => (copy.textContent = data.texts.copied));
})();
