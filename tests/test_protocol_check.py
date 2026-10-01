import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from protocol_check import valid_initialize, valid_oauth_metadata


class DoctorProtocolTest(unittest.TestCase):
    def test_valid_json_and_sse(self):
        body=json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':'2025-06-18','serverInfo':{'name':'fixture'}}})
        self.assertTrue(valid_initialize(body))
        self.assertTrue(valid_initialize('event: message\r\ndata: '+body+'\r\n\r\n'))

    def test_keyword_decoys_errors_and_wrong_rpc_id_are_not_success(self):
        for body in ['{"jsonrpc":"2.0", "result":{}, "protocolVersion":"x", "serverInfo":{}}',
                     '{"jsonrpc":"2.0","id":1,"error":{"result":"protocolVersion serverInfo"}}',
                     '{"jsonrpc":"2.0","id":2,"result":{"protocolVersion":"x","serverInfo":{"name":"fixture"}}}',
                     '{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"x","serverInfo":null}}',
                     'not JSON "jsonrpc":"2.0" "result" "protocolVersion" "serverInfo"']:
            with self.subTest(body=body): self.assertFalse(valid_initialize(body))

    def test_oauth_metadata_must_identify_expected_resource(self):
        self.assertTrue(valid_oauth_metadata(json.dumps({'resource':'https://agent.tinyfish.ai/mcp',
            'authorization_servers':['https://clerk.tinyfish.ai']})))
        for body in [{'resource':'https://wrong.example/mcp','authorization_servers':['https://issuer.example']},
                     {'resource':'https://agent.tinyfish.ai/mcp','authorization_servers':[]},
                     {'resource':'https://agent.tinyfish.ai/mcp','authorization_servers':['http://issuer.example']},
                     {'resource':'https://agent.tinyfish.ai/mcp','authorization_servers':'https://issuer.example'}]:
            with self.subTest(body=body): self.assertFalse(valid_oauth_metadata(json.dumps(body)))
