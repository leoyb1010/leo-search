#!/usr/bin/env python3
"""Bounded public X API v2 search, lookup and timelines. Read-only, no SDK."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib.parse import urlencode, urlsplit, quote
from request_budget import RequestBudget

FIELDS={'tweet.fields':'created_at,author_id,conversation_id,lang,public_metrics,referenced_tweets,entities,note_tweet',
        'expansions':'author_id','user.fields':'username,name'}


def bearer():
    value=os.environ.get('X_BEARER_TOKEN') or os.environ.get('TWITTER_BEARER_TOKEN')
    p=Path.home()/'.config/leo-search/x-bearer-token'
    if not value and p.is_file():value=p.read_text().strip()
    if not value or any(c in value for c in '\r\n'):raise ValueError('X Bearer Token is not configured')
    return value


def post_id(value):
    if value.isdigit() and len(value)<=25:return value
    p=urlsplit(value)
    if p.hostname not in {'x.com','www.x.com','twitter.com','www.twitter.com'}:raise ValueError('Use a numeric post ID or an X/Twitter status URL')
    match=re.search(r'/status/(\d{1,25})(?:/|$)',p.path)
    if not match:raise ValueError('No post ID in URL')
    return match[1]


def get(endpoint,params,budget):
    token=bearer()
    url='https://api.x.com'+endpoint+('?' + urlencode(params) if params else '')
    def request():
        with tempfile.TemporaryDirectory(prefix='leo-x-') as directory:
            headers=Path(directory)/'headers'
            result=subprocess.run(['curl','--silent','--show-error','--connect-timeout','5','--max-time','25',
                '--config','-','--dump-header',str(headers),'--write-out','\n%{http_code}',url],
                input='header = '+json.dumps('Authorization: Bearer '+token)+'\n',capture_output=True,text=True,timeout=27)
            body,_,status=result.stdout.rpartition('\n')
            metadata={}
            if headers.exists():
                for line in headers.read_text().splitlines():
                    name,sep,value=line.partition(':')
                    if sep and name.lower() in {'x-rate-limit-limit','x-rate-limit-remaining','x-rate-limit-reset'}:metadata[name.lower()]=value.strip()
        if result.returncode:raise RuntimeError(f'X transport failed ({result.returncode}); no automatic retry')
        if status!='200':raise RuntimeError(f'X HTTP {status}; check account access/credits or rate reset; no retry loop')
        return json.loads(body),metadata
    return budget.run((endpoint,json.dumps(params,sort_keys=True)),request)


def normalize(data):
    users={u['id']:u for u in data.get('includes',{}).get('users',[])}
    items=data.get('data',[])
    if isinstance(items,dict):items=[items]
    rows=[]
    for item in items:
        author=users.get(item.get('author_id'),{})
        long=item.get('note_tweet') or item.get('note_post') or {}
        rows.append({'id':item['id'],'url':f"https://x.com/{author.get('username','i/web')}/status/{item['id']}",
                     'author':author.get('username'),'author_id':item.get('author_id'),
                     'text':long.get('text') or item.get('text',''),'created_at':item.get('created_at'),
                     'conversation_id':item.get('conversation_id'),'language':item.get('lang'),
                     'metrics':item.get('public_metrics',{}),'references':item.get('referenced_tweets',[]),
                     'links':[x.get('unwound_url') or x.get('expanded_url') or x.get('url') for x in (long.get('entities') or item.get('entities',{})).get('urls',[])],
                     'text_scope':'long_post' if long.get('text') else 'api_text'})
    return rows


def run(args):
    start=time.monotonic();budget=RequestBudget(args.max_requests)
    report={'source':'X official API v2','mode':args.command,'retrieved_at':datetime.now(timezone.utc).isoformat(),
            'posts':[],'pages':[],'cost_dollars':None,'billing_note':'Returned resource count is recorded; exact charges belong to X Developer Console.'}
    try:
        if args.command in {'user','timeline'}:
            username=args.username.lstrip('@')
            if not re.fullmatch(r'[A-Za-z0-9_]{1,15}',username):raise ValueError('Invalid X username')
            user,rate=get('/2/users/by/username/'+quote(username),{'user.fields':'description,created_at,public_metrics'},budget)
            report['user']=user.get('data');report['user_rate_limit']=rate
            if not report['user']:raise ValueError('User not returned')
        if args.command=='user':report['status']='ok'
        else:
            if args.command=='search':
                endpoint='/2/tweets/search/'+('all' if args.archive else 'recent')
                params={**FIELDS,'query':args.query,'max_results':args.limit,'sort_order':args.sort}
                if args.start:params['start_time']=args.start
                if args.end:params['end_time']=args.end
            elif args.command=='post':
                endpoint='/2/tweets';params={**FIELDS,'ids':','.join(dict.fromkeys(post_id(x) for x in args.ids))}
            else:
                endpoint=f"/2/users/{report['user']['id']}/tweets";params={**FIELDS,'max_results':args.limit}
            for _ in range(args.pages if args.command!='post' else 1):
                data,rate=get(endpoint,params,budget)
                rows=normalize(data);report['posts'].extend(rows)
                meta=data.get('meta',{});report['pages'].append({'returned_posts':len(rows),'rate_limit':rate,'errors':data.get('errors',[])})
                report['next_token']=meta.get('next_token')
                if not report['next_token']:break
                params['pagination_token' if args.command=='timeline' else 'next_token']=report['next_token']
            report['posts']=list({p['id']:p for p in report['posts']}.values())
            report['status']='partial' if any(p['errors'] for p in report['pages']) else ('ok' if report['posts'] else 'empty')
            if args.command=='post':
                found={p['id'] for p in report['posts']};report['missing_ids']=[post_id(x) for x in args.ids if post_id(x) not in found]
                if report['missing_ids']:report['status']='partial'
    except (ValueError,RuntimeError,OSError,subprocess.TimeoutExpired) as error:
        report.update({'status':'partial' if report['posts'] else 'unavailable','reason':str(error)[:200]})
    report['requests']={'used':budget.calls,'limit':budget.limit,'reused':budget.cache_hits}
    report['returned_posts']=len(report['posts']);report['latency_ms']=round((time.monotonic()-start)*1000)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ['search','post','user','timeline']:
        s=sub.add_parser(name)
        if name=='search':
            s.add_argument('query');s.add_argument('--archive',action='store_true');s.add_argument('--start');s.add_argument('--end')
            s.add_argument('--sort',choices=['recency','relevancy'],default='recency')
        elif name=='post':s.add_argument('ids',nargs='+')
        else:s.add_argument('username')
        s.add_argument('--limit',type=int,default=10);s.add_argument('--pages',type=int,default=1)
        s.add_argument('--max-requests',type=int,default=4);s.add_argument('--output',type=Path)
    a=p.parse_args()
    if not 10<=a.limit<=100 or not 1<=a.pages<=3 or not 1<=a.max_requests<=6:p.error('limit 10–100, pages 1–3, max requests 1–6')
    if a.command=='post' and len(a.ids)>100:p.error('at most 100 post IDs')
    report=run(a);text=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
    print(text,end='');return 0 if report['status'] in {'ok','empty'} else 2


if __name__=='__main__':raise SystemExit(main())
