from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from codex_probe import isolated_args, summarize


class CodexProbeTest(unittest.TestCase):
    def test_isolation_disables_other_plugins_without_changing_search(self):
        args = isolated_args('[plugins."leo-search@personal"]\nenabled=true\n[plugins."other@personal"]\nenabled=true\n[mcp_servers.browser]\ncommand="browser"\n')
        self.assertIn('plugins.other@personal.enabled=false', args)
        self.assertIn('mcp_servers.browser.enabled=false', args)
        self.assertNotIn('plugins.leo-search@personal.enabled=false', args)

    def test_oauth_metadata_without_tools_is_not_ready(self):
        rows = summarize([{'name': 'leo-search-tinyfish', 'authStatus': 'oAuth', 'tools': {}}], True)
        self.assertEqual(rows[0]['stage'], 'unavailable')
        self.assertIn('reauthorization', rows[0]['reason'])

    def test_zero_auth_service_can_expose_tools_without_login(self):
        rows = summarize([{'name': 'leo-search-exa', 'authStatus': 'notLoggedIn', 'tools': {'web_search_exa': {}}}])
        self.assertEqual(rows[0]['stage'], 'tools_visible')
        self.assertFalse(rows[0]['retrieval_verified'])
