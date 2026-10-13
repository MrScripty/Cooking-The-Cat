#!/usr/bin/env python3
"""Export the approved continuous reading view, then add real PDF download links."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import argparse, shutil, json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args): pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, default=ROOT / 'docs')
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('chromium-browser'))
    args = parser.parse_args(); site = args.site.resolve()
    if site not in [ROOT / 'docs', ROOT / 'dist']: raise ValueError('Site must be the project docs or dist directory')
    if not (site / 'read/index.html').is_file(): raise SystemExit('Build the static site first.')
    review = ROOT / 'review'; review.mkdir(exist_ok=True)
    temporary = review / 'cooking-the-cat.pdf'
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(site)))
    worker = Thread(target=server.serve_forever, daemon=True); worker.start()
    try:
        with sync_playwright() as p:
            launch = {'headless': True, 'args': ['--no-sandbox']}
            if args.browser: launch['executable_path'] = args.browser
            browser = p.chromium.launch(**launch)
            page = browser.new_page()
            response = page.goto(f'http://127.0.0.1:{server.server_port}/read/', wait_until='networkidle')
            assert response.status == 200
            page.emulate_media(media='print')
            page.pdf(path=str(temporary), format='A4', print_background=True, display_header_footer=True,
                     header_template='<span></span>',
                     footer_template='<div style="font-size:8px;width:100%;text-align:center;color:#555">Cooking the Cat · Puma · <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                     margin={'top': '18mm', 'bottom': '20mm', 'left': '18mm', 'right': '18mm'},
                     outline=True, tagged=True)
            browser.close()
    finally:
        server.shutdown(); server.server_close(); worker.join()
    data = temporary.read_bytes()
    assert data.startswith(b'%PDF-') and len(data) > 10000
    target = site / 'downloads/cooking-the-cat.pdf'; target.parent.mkdir(exist_ok=True); target.write_bytes(data)
    changed = 0
    for file in site.rglob('*.html'):
        html = file.read_text()
        if '>Download PDF</a>' in html: continue
        relative = '../' * len(file.parent.relative_to(site).parts)
        markdown = f'<a href="{relative}downloads/cooking-the-cat.md" download>Download Markdown</a>'
        assert html.count(markdown) == 1, file
        html = html.replace(markdown, f'<a href="{relative}downloads/cooking-the-cat.pdf" download>Download PDF</a>' + markdown)
        file.write_text(html); changed += 1
    print(json.dumps({'pdf_bytes': len(data), 'reading_pages_linked': changed}, indent=2))

if __name__ == '__main__': main()
