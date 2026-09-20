#!/usr/bin/env python3
"""Authenticated Exa/Tavily search and extraction; no SDK or persistent service."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from request_budget import RequestBudget

KEY_ROOT=Path.home()/'.config/leo-search'


def credential(provider):
    value=os.environ.get(provider.upper()+'_API_KEY','').strip()
    file=KEY_ROOT/(provider+'-api-key')
    if not value and file.is_file(): value=file.read_text().strip()
    if not value or any(x in value for x in '\r\n'):
        raise ValueError(f'{provider}: no valid local credential; use a configured fallback')
    return value


def post(provider, endpoint, payload, timeout=35):
    key=credential(provider)
    header=('x-api-key: '+key) if provider=='exa' else ('Authorization: Bearer '+key)
    # Put authentication on stdin, not in argv, URLs, source or report files.
    config='header = "Content-Type: application/json"\nheader = '+json.dumps(header)+'\n'
    with tempfile.TemporaryDirectory(prefix='leo-search-request-') as directory:
        data=Path(directory)/'payload.json';data.write_text(json.dumps(payload,ensure_ascii=False))
        result=subprocess.run(['curl','--silent','--show-error','--connect-timeout','5','--max-time',str(timeout),
            '--config','-','--data-binary','@'+str(data),'--write-out','\n%{http_code}',
            f'https://api.{provider}.com/{endpoint}' if provider=='tavily' else f'https://api.exa.ai/{endpoint}'],
            input=config,capture_output=True,text=True,timeout=timeout+2)
    body,_,status=result.stdout.rpartition('\n')
    if result.returncode: raise RuntimeError(f'{provider}: transport failed ({result.returncode}); no automatic chargeable retry')
    if status!='200': raise RuntimeError(f'{provider}: HTTP {status}; change route, do not repeat identical failures')
    return json.loads(body)


def payload_for(provider,args):
    if args.command=='read':
        if provider=='exa':return 'contents',{'urls':args.urls,'text':{'maxCharacters':args.text_characters},'maxAgeHours':0 if args.fresh else 24}
        return 'extract',{'urls':args.urls,'extract_depth':'advanced' if args.mode=='deep' else 'basic','format':'markdown','include_usage':True}
    if provider=='exa':
        payload={'query':args.query,'type':{'fast':'fast','auto':'auto','deep':'deep'}[args.mode],
                 'numResults':args.limit,'contents':{'text':{'maxCharacters':args.text_characters}}}
        if args.include:payload['includeDomains']=args.include
        if args.exclude:payload['excludeDomains']=args.exclude
        if args.after:payload['startPublishedDate']=args.after+'T00:00:00Z'
        if args.before:payload['endPublishedDate']=args.before+'T23:59:59Z'
        if args.category!='general':payload['category']=args.category
        if args.fresh:payload['contents']['maxAgeHours']=0
    else:
        payload={'query':args.query,'search_depth':'advanced' if args.mode=='deep' else 'basic',
                 'max_results':args.limit,'include_answer':False,'include_usage':True,
                 'include_published_date':True,'topic':'news' if args.category=='news' else 'general'}
        if args.include:payload['include_domains']=args.include
        if args.exclude:payload['exclude_domains']=args.exclude
        if args.after:payload['start_date']=args.after
        if args.before:payload['end_date']=args.before
        if args.after or args.before:payload['filter_by_published_date']=True
    return 'search',payload


def call(provider,args,budget):
    started=time.monotonic()
    row={'provider':provider,'mode':args.mode,'scope':'retrieval_only','retrieved_at':datetime.now(timezone.utc).isoformat()}
    try:
        # Missing credentials must not consume a network request.
        credential(provider)
        endpoint,payload=payload_for(provider,args)
        data=budget.run((provider,endpoint,json.dumps(payload,sort_keys=True)),lambda:post(provider,endpoint,payload,60 if args.mode=='deep' else 35))
        rows=[]
        for item in data.get('results',[]):
            content=item.get('text') or item.get('raw_content') or item.get('content') or '\n'.join(item.get('highlights',[]))
            rows.append({'url':item.get('url'),'requested_url':item.get('id') if args.command=='read' and item.get('id') in args.urls else item.get('url'),'title':item.get('title'),
                         'published_at':item.get('publishedDate') or item.get('published_date'),
                         'content':content[:args.text_characters],
                         'content_truncated':True if len(content)>=args.text_characters else None,
                         'content_scope':'provider_excerpt' if args.command=='search' else 'provider_bounded_extraction',
                         'provider_score':item.get('score'),'provider':provider})
        row.update({'results':rows,'status':'ok' if rows else 'empty',
                    'request_id':data.get('requestId') or data.get('request_id'),
                    'usage':data.get('costDollars') or data.get('usage'),
                    'failed_sources':data.get('failed_results',[]),
                    'provider_statuses':data.get('statuses',[]),
                    'limitations':(['Tavily freshness is not guaranteed by --fresh; verify time-critical original pages.'] if provider=='tavily' and args.fresh else [])})
        if args.command=='read':
            successful={url for r in rows if r['content'].strip() for url in (r['url'],r['requested_url']) if url}
            row['missing_requested_urls']=[u for u in args.urls if u not in successful]
            if row['missing_requested_urls']: row['status']='partial' if successful else 'empty'
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
        row.update({'status':'unavailable','reason':str(error)[:200],'results':[]})
    row['latency_ms']=round((time.monotonic()-started)*1000)
    return row


def run(args):
    budget=RequestBudget(args.max_requests)
    if args.provider=='both':
        with ThreadPoolExecutor(2) as pool:rows=list(pool.map(lambda p:call(p,args,budget),['exa','tavily']))
    elif args.provider=='auto':
        rows=[call('exa',args,budget)]
        if rows[0]['status']!='ok':rows.append(call('tavily',args,budget))
    else:rows=[call(args.provider,args,budget)]
    results={}
    for row in rows:
        for item in row['results']:
            if not item['url']:continue
            if item['url'] not in results:results[item['url']]={**item,'retrieved_by':[row['provider']]}
            else:
                results[item['url']]['retrieved_by'].append(row['provider'])
                if len(item['content'])>len(results[item['url']]['content']):
                    results[item['url']]['content']=item['content']
                    results[item['url']]['content_truncated']=item['content_truncated']
    return {'scope':'authenticated_public_retrieval','providers':rows,'results':list(results.values()),
            'requests':{'used':budget.calls,'limit':budget.limit,'reused':budget.cache_hits},
            'note':'Two engines returning one URL are not independent evidence; provider scores are not comparable.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ('search','read'):
        p=sub.add_parser(name)
        p.add_argument('query' if name=='search' else 'urls',nargs=None if name=='search' else '+')
        p.add_argument('--provider',choices=['auto','exa','tavily','both'],default='auto')
        p.add_argument('--mode',choices=['fast','auto','deep'],default='auto')
        p.add_argument('--text-characters',type=int,default=2500)
        p.add_argument('--max-requests',type=int,default=2)
        p.add_argument('--fresh',action='store_true');p.add_argument('--output',type=Path)
        if name=='search':
            p.add_argument('--limit',type=int,default=5)
            p.add_argument('--include',action='append',default=[]);p.add_argument('--exclude',action='append',default=[])
            p.add_argument('--after');p.add_argument('--before')
            p.add_argument('--category',choices=['general','news','publication'],default='general')
    args=parser.parse_args()
    if not 1<=args.max_requests<=20 or not 100<=args.text_characters<=50000:parser.error('request budget 1–20; text limit 100–50000')
    if args.command=='search':
        if not 1<=args.limit<=20:parser.error('result limit must be 1–20')
        for value in (args.after,args.before):
            if value:
                try:datetime.strptime(value,'%Y-%m-%d')
                except ValueError:parser.error('dates must be YYYY-MM-DD')
        if args.after and args.before and args.after>args.before:parser.error('start date must not follow end date')
    report=run(args);rendered=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(rendered)
    print(rendered,end='')
    return 0 if any(r['status']=='ok' for r in report['providers']) else 2


if __name__=='__main__':raise SystemExit(main())
