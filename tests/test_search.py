import argparse
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import search


def args(**extra):
    return argparse.Namespace(**({'command':'search','provider':'auto','mode':'fast','query':'a public question',
        'limit':3,'include':['example.com'],'exclude':[],'after':'2026-01-01','before':None,
        'category':'news','fresh':False,'text_characters':500,'max_requests':2}|extra))


class SearchTest(unittest.TestCase):
    @patch.object(search,'credential',return_value='fake-key')
    def test_fallback_preserves_failure_and_success(self,_):
        def post(provider,*_args):
            if provider=='exa':raise RuntimeError('exa: HTTP 429')
            return {'results':[{'url':'https://example.com/x','content':'evidence','title':'Source'}],'usage':{'credits':1}}
        with patch.object(search,'post',side_effect=post):report=search.run(args())
        self.assertEqual([r['status'] for r in report['providers']],['unavailable','ok'])
        self.assertEqual(report['requests']['used'],2)
        self.assertEqual(report['results'][0]['retrieved_by'],['tavily'])

    @patch.object(search,'credential',return_value='fake-key')
    def test_success_does_not_call_both_by_default(self,_):
        with patch.object(search,'post',return_value={'results':[{'url':'https://example.com','text':'yes'}]}) as post:
            report=search.run(args());self.assertEqual(post.call_count,1)
        self.assertEqual(report['requests']['used'],1)

    def test_dates_and_domain_filters_reach_both_providers(self):
        exa=search.payload_for('exa',args())[1];tav=search.payload_for('tavily',args())[1]
        self.assertEqual(exa['startPublishedDate'],'2026-01-01T00:00:00Z')
        self.assertEqual(tav['start_date'],'2026-01-01');self.assertTrue(tav['filter_by_published_date'])
        self.assertEqual(exa['includeDomains'],tav['include_domains'])

    @patch.object(search,'credential',return_value='secret-test-value')
    @patch.object(search.subprocess,'run')
    def test_key_stays_out_of_process_arguments(self,run,_):
        run.return_value=subprocess.CompletedProcess([],0,'{"results":[]}\n200','')
        search.post('exa','search',{'query':'public'})
        self.assertNotIn('secret-test-value',json.dumps(run.call_args.args[0]))
        self.assertIn('secret-test-value',run.call_args.kwargs['input'])

    @patch.object(search,'credential',return_value='fake-key')
    def test_extraction_cannot_hide_missing_urls(self,_):
        with patch.object(search,'post',return_value={'results':[{'url':'https://example.com/a','text':'readable'}]}):
            report=search.run(args(command='read',provider='exa',urls=['https://example.com/a','https://example.com/b']))
        self.assertEqual(report['providers'][0]['status'],'partial')
        self.assertEqual(report['providers'][0]['missing_requested_urls'],['https://example.com/b'])

    @patch.object(search,'credential',return_value='fake-key')
    def test_budget_prevents_second_network_call(self,_):
        with patch.object(search,'post',side_effect=RuntimeError('HTTP 429')) as post:
            report=search.run(args(max_requests=1));self.assertEqual(post.call_count,1)
        self.assertEqual(report['requests']['used'],1)

    @patch.object(search,'credential',return_value='fake-key')
    def test_provider_limit_is_not_reported_as_complete(self,_):
        with patch.object(search,'post',return_value={'results':[{'url':'https://example.com','text':'x'*500}]}):
            report=search.run(args(provider='exa'))
        self.assertTrue(report['results'][0]['content_truncated'])
        self.assertEqual(report['results'][0]['content_scope'],'provider_excerpt')

    @patch.object(search,'credential',return_value='fake-key')
    def test_extraction_tracks_requested_id_through_canonical_url(self,_):
        with patch.object(search,'post',return_value={'results':[{'id':'http://example.com/a','url':'https://example.com/a','text':'readable original content'}]}):
            report=search.run(args(command='read',provider='exa',urls=['http://example.com/a']))
        self.assertEqual(report['providers'][0]['status'],'ok')
        self.assertEqual(report['results'][0]['requested_url'],'http://example.com/a')
