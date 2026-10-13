/* Local, progressively enhanced book search. No analytics or remote services. */
(() => {
  'use strict';
  const contents = document.querySelector('.book-contents');
  const desktop = window.matchMedia('(min-width: 1000px)');
  if (contents) {
    contents.open = desktop.matches;
    desktop.addEventListener('change', event => { contents.open = event.matches; });
  }
  const dialog = document.querySelector('.search-dialog');
  const open = document.querySelector('.search-open');
  const close = document.querySelector('.search-close');
  const input = document.querySelector('#book-query');
  const status = document.querySelector('.search-status');
  const results = document.querySelector('.search-results');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  let index = null;
  let pending = null;
  let previousFocus = null;
  const root = new URL(document.body.dataset.bookRoot || './', location.href);
  function search() {
    results.replaceChildren();
    const terms = input.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    if (!index) return;
    if (!terms.length) { status.textContent = 'Type to find a passage.'; return; }
    const matches = index.filter(item => terms.every(term => item.haystack.includes(term)))
      .sort((a, b) => Number(terms.every(term => b.title.toLocaleLowerCase().includes(term))) - Number(terms.every(term => a.title.toLocaleLowerCase().includes(term))));
    status.textContent = matches.length ? `${matches.length} matching ${matches.length === 1 ? 'section' : 'sections'}${matches.length > 12 ? '; showing the first 12' : ''}.` : 'No matching sections. Try fewer or different words.';
    for (const item of matches.slice(0, 12)) {
      const at = Math.max(0, item.text.toLocaleLowerCase().indexOf(terms[0]));
      const start = Math.max(0, at - 65);
      const snippet = `${start ? '…' : ''}${item.text.slice(start, start + 220)}${start + 220 < item.text.length ? '…' : ''}`;
      const li = document.createElement('li');
      const link = document.createElement('a');
      const title = document.createElement('strong');
      const excerpt = document.createElement('p');
      link.href = new URL(item.url, root).href;
      title.textContent = item.title;
      excerpt.textContent = snippet;
      link.append(title, excerpt); li.append(link); results.append(li);
    }
  }
  async function show() {
    if (dialog.open) return;
    previousFocus = document.activeElement;
    dialog.showModal(); input.focus();
    if (index) { search(); return; }
    status.textContent = 'Loading the book index…';
    try {
      pending ||= fetch(document.body.dataset.searchIndex).then(response => {
        if (!response.ok) throw new Error('Book index unavailable');
        return response.json();
      });
      index = (await pending).map(item => ({ ...item, haystack: `${item.title} ${item.text}`.toLocaleLowerCase() }));
      search();
    } catch {
      pending = null;
      status.textContent = 'Search could not load. You can still use Contents or your browser’s Find command in the one-page edition.';
    }
  }
  open.hidden = false;
  open.addEventListener('click', show);
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('keydown', event => {
    // A search input can consume Escape to clear its value before the dialog sees it.
    if (event.key === 'Escape') { event.preventDefault(); dialog.close(); }
  });
  dialog.addEventListener('close', () => { if (previousFocus instanceof HTMLElement) previousFocus.focus(); });
  input.addEventListener('input', search);
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !event.target.closest('input,textarea,[contenteditable="true"]') && !dialog.open) {
      event.preventDefault(); show();
    }
  });
})();
