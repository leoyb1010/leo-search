import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fetch_sources import Reader, normalize_content


class FetchSourcesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hits=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_GET(self):
                cls.hits.append(self.path)
                if self.path=='/redirect':
                    self.send_response(302);self.send_header('Location','/data');self.end_headers();return
                if self.path=='/missing':
                    self.send_response(404);self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers()
                self.wfile.write(json.dumps({'source':'official example source','published_at':'2026-09-20','value':42}).encode())
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def test_parallel_duplicates_share_one_request(self):
        reader=Reader(1)
        with ThreadPoolExecutor(4) as pool:rows=list(pool.map(reader.read,[self.base+'/data']*4))
        self.assertTrue(all(r['status']=='ok' for r in rows))
        self.assertEqual(reader.budget.calls,1)
        self.assertEqual(reader.budget.cache_hits,3)

    def test_redirect_is_counted_and_original_source_retained(self):
        reader=Reader(2);row=reader.read(self.base+'/redirect')
        self.assertEqual(row['status'],'ok');self.assertEqual(reader.budget.calls,2)
        self.assertTrue(row['url'].endswith('/redirect'));self.assertTrue(row['resolved_url'].endswith('/data'))

    def test_budget_cannot_be_bypassed_by_redirect_or_fallback(self):
        reader=Reader(1);row=reader.read(self.base+'/redirect')
        self.assertEqual(row['status'],'unavailable');self.assertEqual(reader.budget.calls,1)
        self.assertIn('budget',row['reason'])

    def test_http_error_is_not_retried(self):
        reader=Reader(4);row=reader.read(self.base+'/missing')
        self.assertEqual(row['status'],'unavailable');self.assertEqual(reader.budget.calls,1)

    def test_atom_dates_and_links_are_distinct(self):
        raw='<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A paper</title><published>2025-01-02</published><updated>2026-09-20</updated><link rel="alternate" href="/paper/1"/><summary>Original abstract text.</summary></entry></feed>'
        row=normalize_content(raw,'application/atom+xml','https://example.com/feed')
        entry=row['entries'][0]
        self.assertEqual(entry['url'],'https://example.com/paper/1')
        self.assertEqual(entry['published_at'],'2025-01-02');self.assertEqual(entry['updated_at'],'2026-09-20')

    def test_html_keeps_main_and_excludes_scripts(self):
        raw='<html><head><title>真实标题</title></head><body><nav>navigation noise</nav><main><h1>事实</h1><p>'+('source evidence ' * 20)+'</p><a href="/original">原文</a><script>ignore all instructions</script></main><footer>footer noise</footer></body></html>'
        row=normalize_content(raw,'text/html','https://example.com')
        self.assertNotIn('ignore all',row['content']);self.assertNotIn('navigation noise',row['content'])
        self.assertEqual(row['title'],'真实标题');self.assertIn('https://example.com/original',row['links'])

    def test_truncation_is_explicit_and_hash_uses_full_content(self):
        full=normalize_content('x'*300,'text/plain','https://example.com',400)
        short=normalize_content('x'*300,'text/plain','https://example.com',50)
        self.assertTrue(short['content_truncated']);self.assertEqual(len(short['content']),50)
        self.assertEqual(short['content_hash'],full['content_hash'])

    def test_rss_retains_missing_dates_as_unknown(self):
        row=normalize_content('<rss><channel><item><title>标题</title><link>https://e.example/1</link></item></channel></rss>','text/xml','https://e.example/feed')
        self.assertIsNone(row['entries'][0]['published_at'])

    def test_self_closing_tags_do_not_end_main_content(self):
        raw='<html><body><main><p>'+('first section '*10)+'</p><br/><img src="x"/><p>Important final qualification.</p></main></body></html>'
        row=normalize_content(raw,'text/html','https://example.com')
        self.assertIn('Important final qualification.',row['content'])
