/* kvp-projects.com — small extras on top of pages that work without JavaScript. No requests, no analytics. */
(() => {
  // «Обновлено · x.y.z»: shown while the latest published release is at most 14 days old. The site is rebuilt only
  // when something is published, so the age is checked here, against today.
  const now = Date.now();
  const hash = () => { try { return decodeURIComponent(location.hash.slice(1)); } catch { return ''; } };
  document.querySelectorAll('.fresh[data-released]').forEach((b) => {
    const t = Date.parse(b.dataset.released + 'T00:00:00Z');
    if (t && now - t < 15 * 864e5) b.hidden = false;
  });

  // The support address as text: put together here, not in the page for spam bots. A click still opens mail (the page's own script).
  document.querySelectorAll('a.mail[data-show]').forEach((a) => { a.textContent = a.dataset.u + '@' + a.dataset.d; });

  // /updates/: filter chips (hidden without JS — then everything is shown). #dictum in the address picks an app.
  const chips = document.querySelector('.chips');
  if (chips) {
    const buttons = [...chips.querySelectorAll('button[data-app]')];
    const entries = document.querySelectorAll('.entry[data-app]');
    const pick = (id) => {
      if (!buttons.some((b) => b.dataset.app === id)) id = 'all';
      buttons.forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.app === id)));
      entries.forEach((li) => { li.hidden = id !== 'all' && li.dataset.app !== id; });
      return id;
    };
    chips.addEventListener('click', (ev) => {
      const b = ev.target.closest('button[data-app]');
      if (!b) return;
      const id = pick(b.dataset.app);
      history.replaceState(null, '', id === 'all' ? location.pathname : '#' + id);
    });
    chips.hidden = false;
    pick(hash() || 'all');
    // Back/forward or a link to /updates/#textum on this page: the address changes, the filter follows.
    addEventListener('hashchange', () => pick(hash() || 'all'));
  }

  // A link to an older version (#v0.3.0) unfolds «Предыдущие версии».
  const unfold = () => {
    const id = hash();
    const el = id && document.getElementById(id);
    const d = el && el.closest('details');
    if (d && !d.open) { d.open = true; el.scrollIntoView(); }
  };
  unfold();
  addEventListener('hashchange', unfold);
})();
