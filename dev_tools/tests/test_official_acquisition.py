"""Official origin, text-only acquisition and preservation of the previous library."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import official_docs as official
import resource_manager as resources
import prepare_workspace as prepare
import sync_netease_docs_from_web as sync
from test_maintenance_tools import fixture, docs_source, save


BASE = official.ORIGIN + official.PREFIX
SEED = BASE + 'mcdocs/index.html'
VERSION = BASE + 'mcdocs/1-ModAPI/%E6%9B%B4%E6%96%B0%E4%BF%A1%E6%81%AF/3.9.html'


def article(content='正文'):
    return '<div class="sidebar">导航</div><div class="theme-default-content content__default"><p>' + content + '</p></div>'


class OfficialTests(unittest.TestCase):
    def test_catalog_query_is_normalized_and_beta_or_offsite_ignored(self):
        self.assertEqual(official.official_page('/dev/mcmanual/mc-dev/mcdocs/example.html?catalog=1#title', SEED), BASE + 'mcdocs/example.html')
        for url in ('https://example.invalid/example.html', BASE + 'mcdocs/1-ModAPI-beta/example.html',
                    BASE + 'mcdocs/../../private/example.html', 'http://mc.163.com/dev/mcmanual/mc-dev/mcdocs/example.html'):
            self.assertIsNone(official.official_page(url, SEED))

    def test_article_preserves_code_and_tables_without_images_or_scripts(self):
        parser = official.Article(SEED)
        parser.feed(article('<table><tr><td>字段</td></tr></table><pre><code>a &lt; b</code></pre>'
                            '<img src="data:image/png;base64,SECRET" alt="示例"><script>alert(1)</script><div><p>结尾</p></div>'))
        body = parser.body()
        self.assertIn('<table>', body)
        self.assertIn('a &lt; b', body)
        self.assertIn('结尾', body)
        self.assertIn('图片省略', body)
        for forbidden in ('SECRET', '<img', 'alert(1)', '<script', '导航'):
            self.assertNotIn(forbidden, body)

    def test_missing_or_truncated_article_fails(self):
        for content in ('<h1>请登录</h1>', '<div class="theme-default-content"><p>截断'):
            parser = official.Article(SEED); parser.feed(content)
            with self.assertRaises(resources.ResourceError): parser.body()

    def test_acquisition_publishes_all_families_and_real_source_urls(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            save(root/'docs/SOURCES.json', {'auto_fetch': True, 'usage': 'local-reference-only',
                 'stable_navigation': SEED, 'navigation_seeds': [SEED]})
            links = [VERSION, BASE+'mcguide/example.html', BASE+'mconline/example.html']
            def fetch(url):
                return ''.join('<a href="'+x+'?catalog=1">页面</a>' for x in links) + article() if url == SEED else article('API内容')
            with contextlib.redirect_stderr(io.StringIO()): result = official.fetch_official_docs(root, fetch=fetch)
            self.assertEqual(result['status'], 'READY_LOCAL')
            self.assertEqual(result['images_downloaded'], 0)
            manifest = json.loads((root/'docs/LOCAL_MANIFEST.json').read_text(encoding='utf-8'))
            self.assertEqual(manifest['source_kind'], 'official-web-texts')
            self.assertTrue(all(x['source_url'].startswith(BASE) for x in manifest['files']))
            def forbidden(*args): raise AssertionError('already installed')
            self.assertEqual(official.fetch_official_docs(root, fetch=forbidden)['acquisition'], 'REUSED_LOCAL_TEXTS')

    def test_failed_refresh_preserves_installed_library(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root); resources.import_docs(docs_source(root/'incoming'), root)
            before = (root/'docs/LOCAL_MANIFEST.json').read_bytes()
            save(root/'docs/SOURCES.json', {'auto_fetch': True, 'usage': 'local-reference-only',
                 'stable_navigation': SEED, 'navigation_seeds': [SEED]})
            def offline(url): raise OSError('offline')
            with self.assertRaises(OSError): official.fetch_official_docs(root, refresh=True, fetch=offline)
            self.assertEqual((root/'docs/LOCAL_MANIFEST.json').read_bytes(), before)

    def test_modpc_local_use_is_separate_from_open_license(self):
        row = {'id': 'modpc', 'auto_fetch': True, 'license': {'status': 'redistribution-unverified-local-use-instructions'},
               'revision': 'fixed', 'local_use_basis': {'kind': 'upstream-installation-instructions',
               'redistribution_granted': False, 'source': 'https://github.com/MCNeteaseDevs/ModPC-MCP-Tool/blob/fixed/README.md'}}
        self.assertTrue(resources.remote_allowed(row))
        row['local_use_basis']['source'] = 'https://example.invalid/README.md'
        self.assertFalse(resources.remote_allowed(row))

    def test_status_rejects_fetch_docs_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            with patch.object(official, 'fetch_official_docs', side_effect=AssertionError('network')) as network:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    prepare.main(['--status', '--fetch-docs'], root)
                network.assert_not_called()

    def test_offline_target_is_discovered_and_changes_are_reported_without_downloading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            old = 'https://g79.gdl.netease.com/doc4.zip'
            save(root/'docs/SOURCES.json', {'official_offline_download': {
                'discovery_page': 'https://mc.163.com/download.html', 'observed_url': old,
                'bytes': 42, 'last_modified': '2022-11-11'}})
            def head(url): return {'Content-Length': '42', 'Last-Modified': 'Fri, 11 Nov 2022 10:14:58 GMT'}
            same = sync.check_offline_file(root, fetch=lambda _: '<p>'+old+'</p>', head=head)
            self.assertEqual(same['status'], 'NO_CHANGED_FILE_SIGNATURE')
            changed = sync.check_offline_file(root, fetch=lambda _: '<p>https://g79.gdl.netease.com/doc5.zip</p>', head=head)
            self.assertEqual(changed['status'], 'FILE_METADATA_CHANGED_INSPECT_FORMAL_VERSION')
            self.assertEqual(changed['downloaded_bytes'], 0)

    def test_denial_or_rate_limit_stops_without_retrying(self):
        for code in (401, 403, 429):
            client = official.OfficialHTTP()
            client.opener = Mock()
            client.opener.open.side_effect = HTTPError(SEED, code, 'restricted', {}, None)
            with patch.object(official.time, 'sleep'), self.assertRaises(HTTPError): client(SEED)
            self.assertEqual(client.opener.open.call_count, 1)

    def test_network_retries_are_bounded_and_offsite_requests_never_start(self):
        client = official.OfficialHTTP(); client.opener = Mock()
        client.opener.open.side_effect = URLError('timeout')
        with patch.object(official.time, 'sleep'), self.assertRaises(URLError): client(SEED)
        self.assertEqual(client.opener.open.call_count, 3)
        client.opener.reset_mock()
        with self.assertRaises(resources.ResourceError): client('http://mc.163.com/docs.html')
        client.opener.open.assert_not_called()

    def test_failed_batch_is_resumable_without_partial_library_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            save(root/'docs/SOURCES.json', {'auto_fetch': True, 'usage': 'local-reference-only',
                 'stable_navigation': SEED, 'navigation_seeds': [SEED]})
            links = [VERSION, BASE+'mcguide/example.html', BASE+'mconline/example.html']
            failed = [True]
            calls = []
            def fetch(url):
                calls.append(url)
                if url == SEED: return ''.join('<a href="'+x+'">页面</a>' for x in links) + article()
                if 'mconline' in url and failed[0]: raise OSError('timeout')
                return article()
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(OSError): official.fetch_official_docs(root, fetch=fetch)
            self.assertFalse((root/'docs/LOCAL_MANIFEST.json').exists())
            calls.clear(); failed[0] = False
            with contextlib.redirect_stderr(io.StringIO()): result = official.fetch_official_docs(root, fetch=fetch)
            self.assertEqual(result['status'], 'READY_LOCAL')
            self.assertEqual(calls, [SEED, BASE+'mconline/example.html'])


if __name__ == '__main__':
    unittest.main()
