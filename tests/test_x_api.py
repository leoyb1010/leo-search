import argparse
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import x_api


class XApiTest(unittest.TestCase):
    def test_status_url_and_long_form_text(self):
        self.assertEqual(x_api.post_id('https://x.com/NASA/status/123456?s=20'),'123456')
        with self.assertRaises(ValueError):x_api.post_id('https://example.com/status/123456')
        rows=x_api.normalize({'data':[{'id':'1','text':'short','author_id':'2','note_post':{'text':'complete long post','entities':{'urls':[{'expanded_url':'https://example.com/source'}]}}}], 'includes':{'users':[{'id':'2','username':'NASA'}]}})
        self.assertEqual(rows[0]['text'],'complete long post')
        self.assertEqual(rows[0]['url'],'https://x.com/NASA/status/1')
        self.assertEqual(rows[0]['links'],['https://example.com/source'])

    @patch.object(x_api,'get')
    def test_pagination_is_bounded_and_duplicate_posts_collapse(self,get):
        get.side_effect=[({'data':[{'id':'1','text':'one'}],'meta':{'next_token':'next'}},{}),
                         ({'data':[{'id':'1','text':'one'},{'id':'2','text':'two'}],'meta':{'next_token':'more'}},{})]
        args=argparse.Namespace(command='search',query='AI lang:zh',archive=False,limit=10,sort='recency',start=None,end=None,pages=2,max_requests=2)
        report=x_api.run(args)
        self.assertEqual(get.call_count,2);self.assertEqual(report['returned_posts'],2)
        self.assertEqual(report['next_token'],'more')

    @patch.object(x_api,'get',return_value=({'data':[{'id':'1','text':'one'}],'errors':[{'resource_id':'2','title':'Not Found'}]},{}))
    def test_lookup_does_not_hide_a_missing_post(self,_):
        args=argparse.Namespace(command='post',ids=['1','2'],max_requests=1)
        report=x_api.run(args)
        self.assertEqual(report['status'],'partial');self.assertEqual(report['missing_ids'],['2'])

    @patch.object(x_api,'get',side_effect=RuntimeError('X HTTP 429'))
    def test_rate_limit_does_not_loop(self,get):
        args=argparse.Namespace(command='search',query='AI',archive=False,limit=10,sort='recency',start=None,end=None,pages=3,max_requests=4)
        report=x_api.run(args)
        self.assertEqual(get.call_count,1);self.assertEqual(report['status'],'unavailable')
