#!/usr/bin/env python3
"""Check static routes, fragments, source completeness and publication assets."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote
import argparse, collections, hashlib, json, re
import build

class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.ids=[]; self.links=[]; self.assets=[]; self.headings=[]; self.lang=None; self.errors=[]; self.captures=[]; self.depth=0; self.capture_depth=None; self.tables=0; self.pre=0
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']: self.depth+=1
        if 'id' in a: self.ids.append(a['id'])
        if tag=='html': self.lang=a.get('lang')
        if re.fullmatch('h[1-6]',tag): self.headings.append(int(tag[1]))
        if tag=='a' and 'href' in a: self.links.append(a['href'])
        if tag in ['script','img','link']:
            target=a.get('src') or a.get('href')
            if target:self.assets.append(target)
        if tag=='img' and not a.get('alt'):self.errors.append('Image needs descriptive alt text')
        if tag=='table':self.tables+=1
        if tag=='pre':self.pre+=1
        if 'manuscript-section' in a.get('class','').split():
            assert self.capture_depth is None
            self.capture_depth=self.depth; self.captures.append([])
    def handle_endtag(self,tag):
        if self.capture_depth==self.depth:self.capture_depth=None
        if tag not in ['area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr']:self.depth-=1
    def handle_data(self,data):
        if self.capture_depth is not None:self.captures[-1].append(data)
    def captured(self):return ' '.join(' '.join(' '.join(c) for c in self.captures).split())

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',type=Path,default=build.ROOT/'docs');args=parser.parse_args()
    site=args.site.resolve(); pages={}; errors=[]; local=0; external=set()
    for file in sorted(site.rglob('*.html')):
        page=Page();page.feed(file.read_text());pages[file]=page
        if page.lang!='en':errors.append(f'{file}: missing language')
        if page.headings.count(1)!=1:errors.append(f'{file}: expected exactly one h1')
        if len(page.ids)!=len(set(page.ids)):errors.append(f'{file}: duplicate IDs')
        errors.extend(f'{file}: {e}' for e in page.errors)
    for file,page in pages.items():
        for value in page.links+page.assets:
            url=urlsplit(value)
            if url.scheme or url.netloc:
                if url.scheme not in ['http','https']:errors.append(f'{file}: unexpected URL scheme')
                if value in page.assets:errors.append(f'{file}: external asset')
                external.add(value);continue
            if value.startswith('/'):errors.append(f'{file}: root-relative URL breaks repository Pages')
            dest=(file.parent/unquote(url.path)).resolve() if url.path else file
            if not dest.is_relative_to(site):errors.append(f'{file}: link escapes site');continue
            if dest.is_dir():dest=dest/'index.html'
            if not dest.is_file():errors.append(f'{file}: missing {value}');continue
            if url.fragment and (dest not in pages or unquote(url.fragment) not in pages[dest].ids):errors.append(f'{file}: missing fragment {value}')
            local+=1
    raw=(build.ROOT/'manuscript/cooking-the-cat.md').read_bytes()
    assert (site/'downloads/cooking-the-cat.md').read_bytes()==raw
    original=raw.decode();expected=build.plain(build.MD.render(build.corrected(original)))
    if pages[site/'read/index.html'].captured()!=expected:errors.append('Continuous edition text differs from corrected original')
    lines=original.splitlines(keepends=True)
    for s in build.READERS:
        expected=build.plain(build.MD.render(build.corrected(''.join(lines[s['source_start_line']-1:s['source_end_line']]))))
        actual=pages[site/build.route(s)/'index.html'].captured()
        if actual!=expected:errors.append('Split edition text differs: '+s['title'])
    sources=pages[site/'sources/index.html']; continuous=pages[site/'read/index.html']
    assert all(f'reference-{n}' in sources.ids and f'reference-{n}' in continuous.ids for n in range(1,70))
    original_page=Page();original_page.feed(build.MD.render(original))
    original_external={x for x in original_page.links if x.startswith('http')}
    assert original_external<=external
    assert original_page.tables==continuous.tables==2 and original_page.pre==continuous.pre==1
    assert set(original_page.ids)<=set(continuous.ids)
    assert len(pages)==37
    assert (site/'.nojekyll').exists()
    index=json.loads((site/'search-index.json').read_text());assert len(index)==34
    for entry in index:assert (site/entry['url']/'index.html').is_file() and entry['text']
    # Publication must not contain transfer metadata, credentials or private handoff files.
    banned=[r'libfile_[a-zA-Z0-9]+',r'sediment://',r'X-Amz-Signature=',r'ghp_[a-zA-Z0-9]{20,}',r'github_pat_[a-zA-Z0-9_]+',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    for file in site.rglob('*'):
        if file.is_file() and file.suffix in ['.html','.json','.js','.css','.md']:
            content=file.read_text()
            if any(re.search(pattern,content) for pattern in banned):errors.append('Private metadata or credential pattern in '+str(file))
    report={'html_pages':len(pages),'local_links_and_assets_checked':local,'original_internal_links':sum(x.startswith('#') for x in original_page.links),'original_anchors_preserved':len(original_page.ids),'original_external_urls_preserved':len(original_external),'reference_anchors':69,'original_tables_preserved':2,'original_text_diagrams_preserved':1,'split_and_continuous_text_match':not any('text differs' in e for e in errors),'download_sha256':hashlib.sha256(raw).hexdigest(),'search_sections':len(index),'errors':errors}
    review=build.ROOT/'review';review.mkdir(exist_ok=True);(review/'static-check.json').write_text(json.dumps(report,indent=2)+'\n')
    (review/'external-urls.json').write_text(json.dumps(sorted(external),indent=2)+'\n')
    print(json.dumps(report,indent=2));raise SystemExit(bool(errors))

if __name__=='__main__':main()
