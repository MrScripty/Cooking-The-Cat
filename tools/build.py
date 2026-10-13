#!/usr/bin/env python3
"""Build all reading views from the verified source edition, without network access."""
from pathlib import Path
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlsplit
import argparse, hashlib, json, re, shutil
from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'manuscript/manifest.json').read_text())
SECTIONS = MANIFEST['sections']
MD = MarkdownIt('commonmark', {'html': True}).enable('table')
CORRECTIONS = [
    ('[grouped validation tests]', '[replay and mutation-resistance tests]'),
    ('Complete verification not reached..', 'Complete verification not reached.'),
    ('accepted revision1/proposed2.', 'accepted revision 1/proposed 2.'),
    ('Written-plan-applicability revision is2.', 'Written-plan-applicability revision is 2.'),
]
PRODUCTION_NOTE = ('Prepared with an AI agent from Puma’s engineering conversations and the project research cited here. '
                   'It combines Puma’s stated views with the book’s explanatory synthesis; the examples and exercises are not transcripts of those conversations.')

class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data): self.parts.append(data)
    def value(self): return ' '.join(' '.join(self.parts).split())

def plain(html):
    p = Text(); p.feed(html); return p.value()

def corrected(text):
    for old, new in CORRECTIONS: text = text.replace(old, new)
    return text

def route(section): return section['proposed_relative_route'].split('#')[0]

def prefix(path): return '../' * len([x for x in path.split('/') if x])

def render(text, path, heading='reader', kind='chapter'):
    html = MD.render(corrected(text))
    if heading == 'reader':
        top = min(map(len, re.findall(r'^(#+) ', text, re.M)))
        html = re.sub(r'<(/?)h([1-6])>', lambda m: f'<{m[1]}h{1 if int(m[2]) == top else min(6, int(m[2]) - top + 1)}>', html)
        # Reference headings are h3 in the original; keep a sequential h1/h2 outline.
        if kind == 'sources': html = html.replace('<h3>', '<h2>').replace('</h3>', '</h2>')
    elif heading == 'part':
        html = re.sub(r'<h1>(.*?)</h1>', r'<p class="part-title">\1</p>', html)
    elif heading == 'continuous':
        top = min(map(len, re.findall(r'^(#+) ', text, re.M)))
        target = 1 if kind == 'title' else (3 if kind == 'chapter' else 2)
        html = re.sub(r'<(/?)h([1-6])>', lambda m: f'<{m[1]}h{target if int(m[2]) == top else min(6, target + 1)}>', html)
    if path != 'read/':
        def rewrite(m):
            anchor = m[1]
            if anchor not in ANCHORS: raise ValueError('Unknown fragment: ' + anchor)
            return 'href="' + escape(prefix(path) + ANCHORS[anchor], quote=True) + '"'
        html = re.sub(r'href="#([^"]+)"', rewrite, html)
    html = re.sub(r'<h([23])>Reference (\d+)</h\1>', lambda m: f'<h{m[1]} id="reference-{m[2]}">Reference {m[2]}</h{m[1]}>', html)
    # Preserve visible source labels and add contextual accessible names.
    ref = 0
    def source_name(m):
        nonlocal ref
        ref += 1
        return f'<a href="{m[1]}" aria-label="Open source for reference {ref}">Open source</a>'
    if kind == 'sources': html = re.sub(r'<a href="([^"]+)">Open source</a>', source_name, html)
    html = html.replace('<table>', '<div class="overflow-region" role="region" aria-label="Book table" tabindex="0"><table>').replace('</table>', '</table></div>')
    html = html.replace('<pre>', '<pre tabindex="0" aria-label="Development path text diagram">')
    return html

ANCHORS = {s['anchor']: (route(s) + '#' + s['anchor']) for s in SECTIONS}
ANCHORS['title'] = '#title'; ANCHORS['contents'] = '#contents'
READERS = [s for s in SECTIONS if s['kind'] in ['preface', 'chapter', 'vocabulary', 'sources']]
PARTS = [s for s in SECTIONS if s['kind'] == 'part']

def toc(path, current=None, landing=False):
    pre = prefix(path)
    links = [f'<a class="front-link" href="{pre}preface/"' + (' aria-current="page"' if current == 'preface' else '') + '>Preface</a>']
    for part in PARTS:
        chapters = [s for s in READERS if s.get('part') == part['part']]
        items = ''.join(f'<li><a href="{pre}{route(s)}"' + (' aria-current="page"' if s['anchor'] == current else '') + f'><span class="chapter-number">{s["chapter"]:02}</span><span>{escape(re.sub(r"^\d+ ", "", s["title"]))}</span></a></li>' for s in chapters)
        title = re.sub(r'^Part \d+ ', '', part['title'])
        links.append(f'<section class="toc-part"><h3><span>PART {part["part"]:02}</span>{escape(title)}</h3><ol start="{chapters[0]["chapter"]}">{items}</ol></section>')
    links.append('<div class="back-links">' + ''.join(f'<a href="{pre}{route(s)}"' + (' aria-current="page"' if s['anchor'] == current else '') + f'>{escape(s["title"])}</a>' for s in READERS[-2:]) + '</div>')
    return '<nav aria-label="Book contents" class="contents-list' + (' contents-grid' if landing else '') + '">' + ''.join(links) + '</nav>'

def shell(title, path, body, current=None, sidebar=False):
    pre = prefix(path)
    aside = f'<aside class="sidebar"><details class="book-contents"><summary>Contents <span aria-hidden="true">＋</span></summary>{toc(path, current)}</details></aside>' if sidebar else ''
    canonical = f'<link rel="canonical" href="{escape(ARGS.public_base.rstrip("/") + "/" + path)}">' if ARGS.public_base else ''
    source = f'<a href="{escape(ARGS.source_repository)}">Source</a>' if ARGS.source_repository else ''
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><meta name="description" content="{escape(MANIFEST['subtitle'])}"><title>{escape(title)} · Cooking the Cat</title>{canonical}<link rel="stylesheet" href="{pre}{CSS}"><script src="{pre}{JS}" defer></script></head>
<body data-search-index="{pre}search-index.json" data-book-root="{pre}"><a class="skip-link" href="#main">Skip to reading</a>
<header class="site-header"><a class="wordmark" href="{pre or './'}">Cooking the Cat <span>PUMA</span></a><nav aria-label="Reading tools"><a href="{pre}#contents">Contents</a><a href="{pre}read/">Read in one page</a><button class="search-open" type="button" hidden>Search</button></nav></header>
<div class="page-shell{' reader-shell' if sidebar else ''}">{aside}<main id="main" tabindex="-1">{body}</main></div>
<footer class="site-footer"><span>Puma · Edition 2 October 2026</span><nav aria-label="Book links"><a href="https://mrscripty.github.io/MrScripty/">Puma’s projects</a><a href="{pre}downloads/cooking-the-cat.md" download>Download Markdown</a>{source}<a href="{pre}edition/">Edition notes</a></nav></footer>
<dialog class="search-dialog" aria-labelledby="search-title"><div class="search-heading"><h2 id="search-title">Search the book</h2><button class="search-close" type="button" aria-label="Close book search">Close ×</button></div><label for="book-query">Words or a chapter title</label><input id="book-query" type="search" autocomplete="off"><p class="search-status" role="status" aria-live="polite">Type to find a passage.</p><ol class="search-results"></ol></dialog>
</body></html>'''

def write(path, html):
    p = OUT / path / 'index.html'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(html)

def main():
    global ARGS, OUT, CSS, JS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--require-cover', action='store_true')
    parser.add_argument('--public-base', default='')
    parser.add_argument('--source-repository', default='')
    ARGS = parser.parse_args(); OUT = ARGS.output.resolve()
    if OUT not in [ROOT / 'docs', ROOT / 'dist']: raise ValueError('Output must be the project docs or dist directory')
    data = (ROOT / 'manuscript/cooking-the-cat.md').read_bytes()
    assert len(data) == MANIFEST['source_bytes'] and hashlib.sha256(data).hexdigest() == MANIFEST['source_sha256']
    original = data.decode(); lines = original.splitlines(keepends=True); chunks = {}
    for s in SECTIONS:
        chunk = ''.join(lines[s['source_start_line'] - 1:s['source_end_line']]); raw = chunk.encode()
        assert len(raw) == s['size_bytes'] and hashlib.sha256(raw).hexdigest() == s['sha256'], s['title']
        chunks[s['anchor']] = chunk
    assert ''.join(chunks[s['anchor']] for s in SECTIONS) == original
    for old, _ in CORRECTIONS: assert original.count(old) == 1, old
    cover = ROOT / 'web/assets/cooking-the-cat-cover.png'
    if ARGS.require_cover and not cover.is_file(): raise SystemExit('Publication blocked: approved cover bytes have not been recovered and inspected.')
    if OUT.exists(): shutil.rmtree(OUT)
    (OUT / 'assets').mkdir(parents=True); (OUT / 'downloads').mkdir()
    for name in ['styles.css', 'reader.js']:
        asset = (ROOT / 'web' / name).read_bytes(); stem, suffix = name.split('.')
        dest = f'assets/{stem}.{hashlib.sha256(asset).hexdigest()[:12]}.{suffix}'; (OUT / dest).write_bytes(asset)
        if suffix == 'css': CSS = dest
        else: JS = dest
    (OUT / '.nojekyll').write_text(''); (OUT / 'downloads/cooking-the-cat.md').write_bytes(data)
    cover_html = ''
    if cover.is_file():
        shutil.copyfile(cover, OUT / 'assets/cooking-the-cat-cover.png')
        cover_html = '<img class="book-cover" src="assets/cooking-the-cat-cover.png" width="1024" height="1536" alt="Cooking the Cat, by Puma — illustrated cover">'
    hero = f'<section class="book-hero" id="title"><div><p class="eyebrow">PUMA · 2 OCTOBER 2026</p><h1>Cooking<br>the Cat<span class="title-dot" aria-hidden="true">.</span></h1><p class="subtitle">{escape(MANIFEST["subtitle"])}</p><div class="hero-actions"><a class="primary-link" href="preface/">Start reading <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 13 13 3M3 3h10v10" stroke="currentColor" stroke-width="1.5"/></svg></a><a href="#contents">Explore the contents</a></div><p class="book-meta">Six parts · 31 chapters · 69 references</p></div>{cover_html}</section>'
    contents = f'<section class="landing-contents" id="contents"><p class="eyebrow">THE BOOK</p><h2>From intent to evidence.</h2>{toc("", landing=True)}</section>'
    note = f'<section class="production-note"><h2>About this edition</h2><p>{escape(PRODUCTION_NOTE)}</p><a href="edition/">Edition notes</a></section>'
    write('', shell(MANIFEST['title'], '', hero + contents + note))
    search = []; completeness = []
    for i, s in enumerate(READERS):
        path = route(s); content = ''
        part = next((p for p in PARTS if route(p) == path), None)
        if part: content += '<section class="part-intro manuscript-part">' + render(chunks[part['anchor']], path, 'part') + '</section>'
        main_html = render(chunks[s['anchor']], path, kind=s['kind'])
        content += '<article class="reading-content manuscript-section">' + main_html + '</article>'
        pager = []
        for direction, index in [('Previous', i - 1), ('Next', i + 1)]:
            if 0 <= index < len(READERS):
                dest = READERS[index]; pager.append(f'<a class="pager-{direction.lower()}" href="{prefix(path)}{route(dest)}"><span>{direction}</span>{escape(dest["title"])}</a>')
        content += '<nav class="chapter-pager" aria-label="Chapter navigation">' + ''.join(pager) + '</nav>'
        write(path, shell(s['title'], path, content, s['anchor'], True))
        search.append({'title': s['title'], 'url': path, 'text': plain((render(chunks[part['anchor']], path, 'part') if part else '') + main_html)})
        expected = plain(MD.render(corrected(chunks[s['anchor']])))
        assert plain(main_html) == expected, s['title']
        completeness.append({'anchor': s['anchor'], 'route': path, 'source_sha256': s['sha256'], 'text_matches_corrected_source': True})
    continuous = ''.join('<section class="continuous-section manuscript-section">' + render(chunks[s['anchor']], 'read/', 'continuous', s['kind']) + '</section>' for s in SECTIONS)
    write('read/', shell('Continuous reading', 'read/', '<article class="continuous-reading">' + continuous + '</article>'))
    notes = '<article class="reading-content"><h1>Edition notes</h1><p>' + escape(PRODUCTION_NOTE) + '</p><p>The manuscript is dated 2 October 2026. The principles-focused public revision was approved on 13 October 2026. Its cited source revisions, historical observations and stated evidence limits are preserved.</p><h2>Small corrections in this web edition</h2><ul>' + ''.join('<li><span class="before">' + escape(a) + '</span> → ' + escape(b) + '</li>' for a,b in CORRECTIONS) + '</ul><p>The downloadable Markdown contains the approved public manuscript. This public revision keeps the focus on engineering principles; technical case studies serve as supporting evidence. The reading views add the small corrections listed above and navigation changes.</p><p>The repository includes the owner-provided Apache License 2.0. Source references do not expand the licenses of third-party works.</p></article>'
    write('edition/', shell('Edition notes', 'edition/', notes))
    (OUT / 'search-index.json').write_text(json.dumps(search, ensure_ascii=False) + '\n')
    report = {'source_sha256': MANIFEST['source_sha256'], 'source_bytes': len(data), 'sections': len(SECTIONS), 'chapters': 31, 'parts': 6, 'references': 69, 'reading_pages': len(READERS), 'html_pages': len(list(OUT.rglob('*.html'))), 'approved_cover_present': cover.is_file(), 'corrections': CORRECTIONS, 'source_reassembles_exactly': True, 'reader_text': completeness}
    review = ROOT / 'review'; review.mkdir(exist_ok=True); (review / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['reader_text','corrections']}, indent=2))

if __name__ == '__main__': main()
