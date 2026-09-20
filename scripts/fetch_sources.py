#!/usr/bin/env python3
"""Read a small batch of public HTML, JSON or RSS/Atom sources without a provider account."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from request_budget import RequestBudget

VOID_TAGS={'br','hr','img','meta','input','link','source','wbr','area','base','embed','param','track','col'}


class PageText(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.parts, self.main, self.links = base, [], [], []
        self.skip = 0
        self.depth = 0
        self.main_depth = None
        self.title, self.in_title, self.published_at = '', False, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in VOID_TAGS:
            self.depth += 1
        if tag in {'script','style','noscript','svg','nav','footer'}:
            self.skip += 1
        if tag == 'title': self.in_title = True
        if tag in {'main','article'} or attrs.get('role') == 'main':
            if self.main_depth is None: self.main_depth = self.depth
        if tag == 'meta' and attrs.get('property', attrs.get('name')) in {'article:published_time','datePublished'}:
            self.published_at = attrs.get('content')
        if tag == 'a' and attrs.get('href') and not self.skip:
            url = urljoin(self.base, attrs['href'])
            if urlsplit(url).scheme in {'http','https'} and url not in self.links: self.links.append(url)
        if tag in {'p','div','br','li','h1','h2','h3','h4','tr','section'}: self.handle_data('\n')

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:return
        if tag == 'title': self.in_title = False
        if self.main_depth is not None and self.depth <= self.main_depth: self.main_depth = None
        if tag in {'script','style','noscript','svg','nav','footer'}: self.skip = max(0,self.skip-1)
        self.depth = max(0,self.depth-1)
        if tag in {'p','div','li','h1','h2','h3','tr','section'}: self.handle_data('\n')

    def handle_data(self, data):
        if self.in_title: self.title += data
        if not self.skip:
            self.parts.append(data)
            if self.main_depth is not None: self.main.append(data)


def normalize_content(raw, content_type, url, limit=12000):
    """Preserve source dates and feed links; do not infer factual accuracy."""
    stripped = raw.lstrip()
    if 'json' in content_type or stripped.startswith(('{','[')):
        value = json.loads(raw)
        content = json.dumps(value, ensure_ascii=False, indent=2)
        data = {'format':'json','title':urlsplit(url).netloc}
    elif 'xml' in content_type or stripped.startswith(('<?xml','<rss','<feed')):
        root = ET.fromstring(raw)
        entries = []
        for item in root.findall('.//item') + root.findall('{*}entry'):
            def text(tag):
                node = item.find(tag)
                if node is None: node = item.find('{*}'+tag)
                return ''.join(node.itertext()).strip() if node is not None else None
            link = text('link')
            if not link:
                node = next((n for n in item.findall('{*}link') if n.get('rel','alternate')=='alternate'),None)
                link = node.get('href') if node is not None else None
            entries.append({'title':text('title'),'url':urljoin(url,link) if link else None,
                            'published_at':text('published') or text('pubDate'), 'updated_at':text('updated'),
                            'summary':text('summary') or text('description')})
        content = json.dumps(entries,ensure_ascii=False,indent=2)
        data = {'format':'feed','title':urlsplit(url).netloc,'entries':entries[:20],
                'entry_count':len(entries),'entries_truncated':len(entries)>20}
    elif 'html' in content_type or re.match(r'(?is)<!doctype\s+html|<html',stripped):
        parser = PageText(url); parser.feed(raw)
        preferred = ''.join(parser.main)
        content = preferred if len(preferred.strip())>=80 else ''.join(parser.parts)
        content = '\n'.join(re.sub(r'[ \t]+',' ',line).strip() for line in content.splitlines() if line.strip())
        data = {'format':'html','title':parser.title.strip(),'links':parser.links[:60],
                'published_at':parser.published_at, 'links_truncated':len(parser.links)>60}
    else:
        content = raw
        data = {'format':'text','title':urlsplit(url).netloc}
    return {**data,'content':content[:limit],'characters':len(content),
            'content_truncated':len(content)>limit,'content_hash':hashlib.sha256(content.encode()).hexdigest()}


class Reader:
    def __init__(self, budget=12, timeout=10, limit=12000):
        self.budget = RequestBudget(budget)
        self.timeout, self.limit = timeout, limit
        self.preferred = {}

    def request(self, url, proxy=False):
        # Single-flight shares public response bytes only for this process.
        return self.budget.run((url,proxy),lambda:self._request(url,proxy))

    def _request(self, url, proxy):
        command = ['curl','--silent','--show-error','--compressed','--connect-timeout','3',
                   '--max-time',str(self.timeout),'--max-filesize','2097152',
                   '-H','User-Agent: LeoSearch/1.6 public-source-reader',
                   '--write-out','\nLEO_META:%{http_code}\t%{content_type}\t%{redirect_url}']
        if proxy:
            command = [str(Path(__file__).with_name('with_proxy.sh')),*command]
        else: command += ['--noproxy','*']
        result = subprocess.run([*command,url],capture_output=True,timeout=self.timeout+2)
        raw, separator, meta = result.stdout.rpartition(b'\nLEO_META:')
        if result.returncode or not separator:
            raise RuntimeError(f'transport failed (curl {result.returncode})')
        status, content_type, redirect = meta.decode().split('\t',2)
        charset = re.search(r'charset=([\w-]+)',content_type,re.I)
        try: text = raw.decode(charset[1] if charset else 'utf-8',errors='replace')
        except LookupError: text = raw.decode('utf-8',errors='replace')
        return int(status),content_type,redirect,text

    def read(self, original):
        start = time.monotonic()
        row = {'url':original,'retrieved_at':datetime.now(timezone.utc).isoformat(),
               'scope':'retrieval_only','attempts':[]}
        url = original
        try:
            for _ in range(4):
                if urlsplit(url).scheme not in {'http','https'}: raise ValueError('only public HTTP(S) URLs are supported')
                host = urlsplit(url).netloc
                use_proxy = self.preferred.get(host,False)
                try:
                    row['attempts'].append({'url':url,'route':'configured-proxy' if use_proxy else 'direct'})
                    status,content_type,redirect,raw = self.request(url,use_proxy)
                except (RuntimeError,subprocess.TimeoutExpired) as error:
                    if 'budget exhausted' in str(error): raise
                    has_proxy = (Path.home()/'.config/leo-search/proxy').is_file() or any(os.environ.get(k) for k in ('LEO_SEARCH_PROXY','HTTPS_PROXY','ALL_PROXY'))
                    if use_proxy or not has_proxy: raise
                    row['attempts'].append({'url':url,'route':'configured-proxy'})
                    status,content_type,redirect,raw = self.request(url,True)
                    if 200<=status<400: self.preferred[host]=True
                if status in {301,302,303,307,308} and redirect:
                    url=urljoin(url,redirect);continue
                row.update({'resolved_url':url,'http_status':status,'content_type':content_type})
                if not 200<=status<300: raise ValueError(f'HTTP {status}; change source or report boundary, do not loop')
                if any(t in content_type for t in ('application/pdf','image/','audio/','video/')):
                    row.update({'status':'specialized_reader_required','reason':content_type});break
                row.update(normalize_content(raw,content_type,url,self.limit))
                row['status']='ok' if row['characters']>=40 else 'thin_content'
                break
            else: raise ValueError('redirect limit exceeded')
        except (RuntimeError,ValueError,OSError,subprocess.TimeoutExpired,ET.ParseError) as error:
            row.update({'status':'unavailable','reason':str(error)[:180]})
        row['latency_ms']=round((time.monotonic()-start)*1000)
        return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('urls',nargs='+');p.add_argument('--max-requests',type=int,default=12)
    p.add_argument('--max-characters',type=int,default=12000);p.add_argument('--timeout',type=int,default=10)
    p.add_argument('--output',type=Path);a=p.parse_args()
    if min(a.max_requests,a.max_characters,a.timeout)<1:p.error('budgets must be positive')
    reader=Reader(a.max_requests,a.timeout,a.max_characters)
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(reader.read,a.urls))
    report={'scope':'public_source_batch','sources':rows,
            'requests':{'used':reader.budget.calls,'limit':reader.budget.limit,'reused':reader.budget.cache_hits}}
    rendered=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(rendered)
    print(rendered,end='')
    return 0 if all(r['status']=='ok' for r in rows) else 2


if __name__=='__main__':raise SystemExit(main())
