"""Fault-path regressions for preparation, document imports and readiness."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_workspace as prepare
import resource_manager as resources
import sync_netease_docs_from_web as sync
import verify_local_environment as verify
import export_template as exporter


def record(name, content):
    return {'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding='utf-8')


def fixture(root, allowed=True):
    row = {'id': 'example', 'destination': 'dev_tools/external/example', 'kind': 'files', 'auto_fetch': allowed,
           'license': {'status': 'verified' if allowed else 'unverified'}, 'primary': 'main.py',
           'files': [dict(record('main.py', b'answer = 42\n'), url='https://example.invalid/main.py')]}
    save(root/'dev_tools/manifests/resources.json', {'resources': [row]})
    save(root/'docs/SOURCES.json', {'auto_fetch': False, 'stable_navigation': 'https://mc.163.com/dev/mcmanual/mc-dev/mcdocs/index.html'})
    core = root/'README.md'
    core.write_text('core\n', encoding='utf-8')
    save(root/'dev_tools/manifests/distribution_manifest.json', {'files': [record('README.md', core.read_bytes())]})
    return row


def docs_source(root):
    for name in ('mcdocs/1-ModAPI/接口/example.md', 'mcguide/example.md', 'mconline/example.md', 'mcdocs/1-ModAPI/更新信息/3.9.md'):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('正文与 API 示例\n', encoding='utf-8')
    return root


class PreparationTests(unittest.TestCase):
    def test_clean_source_pass_is_not_api_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            self.assertEqual(verify.verify(root)['result'], 'PASS')
            self.assertEqual(verify.verify(root, task='api')['result'], 'NOT_READY')
            self.assertFalse(verify.verify(root)['readiness']['api_contracts_verified'])

    def test_full_profile_requires_missing_resources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            self.assertEqual(verify.verify(root, profile='full')['result'], 'FAIL')

    def test_missing_core_is_always_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root); (root/'README.md').unlink()
            self.assertEqual(verify.verify(root)['result'], 'FAIL')

    def test_unverified_resource_never_downloads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root, allowed=False)
            with patch.object(resources, 'download', side_effect=AssertionError('network')) as network:
                with self.assertRaisesRegex(resources.ResourceError, 'MANUAL_SOURCE_REQUIRED'):
                    resources.install_resource(row, root)
                network.assert_not_called()

    def test_existing_file_at_tool_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);row=fixture(root);target=root/row['destination'];target.parent.mkdir(parents=True);target.write_bytes(b'keep')
            with self.assertRaises(resources.ResourceError):resources.install_resource(row,root)
            self.assertEqual(target.read_bytes(),b'keep')

    def test_fetch_and_repeat_are_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root)
            def fetch(url, target, expected): target.write_bytes(b'answer = 42\n')
            self.assertEqual(resources.install_resource(row, root, downloader=fetch)['status'], 'INSTALLED')
            def forbidden(*args): raise AssertionError('repeat download')
            self.assertEqual(resources.install_resource(row, root, downloader=forbidden)['status'], 'ALREADY_PRESENT')

    def test_download_failure_preserves_existing_partial_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root)
            row['files'].append(dict(record('second.py', b'second\n'), url='https://example.invalid/second.py'))
            path = root/row['destination']/'main.py'; path.parent.mkdir(parents=True); path.write_bytes(b'answer = 42\n')
            def broken(url, target, expected): raise OSError('offline')
            with self.assertRaises(OSError): resources.install_resource(row, root, downloader=broken)
            self.assertEqual(path.read_bytes(), b'answer = 42\n')
            self.assertFalse((path.parent/'second.py').exists())

    def test_hash_failure_never_publishes_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root)
            def wrong(url, target, expected): target.write_bytes(b'wrong')
            with self.assertRaises(resources.ResourceError): resources.install_resource(row, root, downloader=wrong)
            self.assertFalse((root/row['destination']).exists())

    def test_modified_resource_fails_even_in_source_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root)
            path = root/row['destination']/'main.py'; path.parent.mkdir(parents=True); path.write_text('changed')
            self.assertEqual(verify.verify(root)['result'], 'FAIL')

    def test_unrelated_broken_optional_tool_does_not_block_api_resource_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);row=fixture(root);source=docs_source(root/'incoming');resources.import_docs(source,root)
            path=root/row['destination']/'main.py';path.parent.mkdir(parents=True);path.write_text('changed')
            self.assertEqual(verify.verify(root,task='api')['result'],'PASS')
            self.assertEqual(verify.verify(root)['result'],'FAIL')

    def test_explicit_repair_preserves_old_copy(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root)
            path = root/row['destination']/'main.py'; path.parent.mkdir(parents=True); path.write_bytes(b'changed')
            def fetch(url, target, expected): target.write_bytes(b'answer = 42\n')
            with self.assertRaises(resources.ResourceError): resources.install_resource(row, root, downloader=fetch)
            result = resources.install_resource(row, root, downloader=fetch, repair=True)
            self.assertTrue(result['previous_copy_preserved'])
            self.assertEqual(next((root/'dev_tools/local_state/backups').glob('*/main.py')).read_bytes(), b'changed')

    def test_unverified_local_import_has_no_remote_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); row = fixture(root, allowed=False)
            source = root/'provided'; source.mkdir(); (source/'main.py').write_bytes(b'answer = 42\n')
            def forbidden(*args): raise AssertionError('network')
            self.assertEqual(resources.install_resource(row, root, source, downloader=forbidden)['source'], 'local-import')

    def test_status_does_not_import_environment_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); fixture(root)
            with patch.dict('os.environ', {'NETEASE_DOCS_SOURCE': str(root/'missing')}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(prepare.main(['--status', '--task', 'api'], root), 2)
            self.assertFalse((root/'docs/LOCAL_MANIFEST.json').exists())

    def test_export_uses_public_allowlist_even_after_local_preparation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            cached=root/'dev_tools/external/private.txt';cached.parent.mkdir(parents=True);cached.write_text('local data')
            destination=root/'out.zip';exporter.export(root,destination)
            with zipfile.ZipFile(destination) as package:
                self.assertEqual(set(package.namelist()),{'README.md','dev_tools/manifests/distribution_manifest.json'})

    def test_export_refuses_existing_output_without_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);destination=root/'out.zip';destination.write_bytes(b'previous')
            with self.assertRaises(resources.ResourceError):exporter.export(root,destination)
            self.assertEqual(destination.read_bytes(),b'previous')

    def test_export_rejects_manifest_that_accidentally_includes_cache(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            cached=root/'dev_tools/external/accidental.txt';cached.parent.mkdir(parents=True);cached.write_bytes(b'cache')
            manifest=root/'dev_tools/manifests/distribution_manifest.json';data=json.loads(manifest.read_text())
            data['files'].append(record('dev_tools/external/accidental.txt',b'cache'));save(manifest,data)
            with self.assertRaises(resources.ResourceError):exporter.export(root,root/'out.zip')


class ArchiveTests(unittest.TestCase):
    def check_rejected(self, names, symlink=False):
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, 'w') as package:
            for name in names:
                item = zipfile.ZipInfo(name)
                if symlink: item.create_system=3; item.external_attr=(stat.S_IFLNK | 0o777)<<16
                package.writestr(item, b'content')
        memory.seek(0)
        with zipfile.ZipFile(memory) as package, self.assertRaises(resources.ResourceError): resources.zip_members(package)

    def test_parent_traversal(self): self.check_rejected(['root/../escape.py'])
    def test_windows_drive(self): self.check_rejected(['C:/escape.py'])
    def test_windows_backslash_traversal(self): self.check_rejected(['root\\..\\escape.py'])
    def test_case_collision(self): self.check_rejected(['root/Code.py', 'root/code.py'])
    def test_windows_reserved_name(self): self.check_rejected(['root/NUL.txt'])
    def test_symbolic_link(self): self.check_rejected(['root/link'], symlink=True)


class DocumentTests(unittest.TestCase):
    def test_import_filters_images_and_records_real_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); fixture(root); source=docs_source(root/'incoming')
            (source/'mcguide/photo.png').write_bytes(b'image')
            result=resources.import_docs(source, root)
            self.assertEqual(result['status'], 'READY_LOCAL'); self.assertEqual(result['files'], 4)
            self.assertFalse((root/'docs/mcguide/photo.png').exists())
            self.assertEqual(result['formal_versions'], ['3.9'])
            self.assertFalse(result['api_contracts_verified'])

    def test_partial_import_is_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); fixture(root); source=root/'incoming/mcguide';source.mkdir(parents=True);(source/'one.md').write_text('text')
            self.assertEqual(resources.import_docs(source.parent, root)['status'], 'PARTIAL')

    def test_partial_import_cli_returns_not_ready(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=root/'incoming/mcguide';source.mkdir(parents=True);(source/'one.md').write_text('text')
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(prepare.main(['--docs-source',str(source.parent)],root),2)

    def test_binary_disguised_as_text_is_not_installed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=root/'incoming/mcguide';source.mkdir(parents=True);(source/'broken.md').write_bytes(b'\xff\xfe\x80')
            with self.assertRaises(resources.ResourceError):resources.import_docs(source.parent,root)
            self.assertFalse((root/'docs/LOCAL_MANIFEST.json').exists())

    def test_import_preserves_historical_texts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=docs_source(root/'incoming');resources.import_docs(source, root)
            (source/'mcguide/example.md').unlink();(source/'mconline/example.md').write_text('new')
            self.assertEqual(resources.import_docs(source,root)['status'],'READY_LOCAL')
            self.assertTrue((root/'docs/mcguide/example.md').is_file())

    def test_identical_document_import_reuses_existing_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=docs_source(root/'incoming');resources.import_docs(source,root)
            before=(root/'docs/LOCAL_MANIFEST.json').read_bytes()
            resources.import_docs(source,root)
            self.assertEqual((root/'docs/LOCAL_MANIFEST.json').read_bytes(),before)
            self.assertFalse((root/'dev_tools/local_state/backups').exists())

    def test_changed_local_document_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=docs_source(root/'incoming');resources.import_docs(source,root)
            path=root/'docs/mcguide/example.md';path.write_text('local edit')
            with self.assertRaises(resources.ResourceError):resources.import_docs(source,root)
            self.assertEqual(path.read_text(),'local edit')

    def test_unsafe_document_zip_is_rejected_before_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);archive=root/'incoming.zip'
            with zipfile.ZipFile(archive,'w') as package:package.writestr('docs/mcdocs/../../evil.md','x')
            with self.assertRaises(resources.ResourceError):resources.import_docs(archive,root)
            self.assertFalse((root/'evil.md').exists())

    def test_valid_document_zip_import(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);archive=root/'incoming.zip'
            with zipfile.ZipFile(archive,'w') as package:
                for name in ('mcdocs/1-ModAPI/one.md','mcguide/one.md','mconline/one.md'):package.writestr('export/docs/'+name,'text')
            self.assertEqual(resources.import_docs(archive,root)['status'],'READY_LOCAL')

    def test_manifest_write_failure_rolls_back_document_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=docs_source(root/'incoming');resources.import_docs(source,root)
            previous=(root/'docs/LOCAL_MANIFEST.json').read_bytes();before=(root/'docs/mcguide/example.md').read_bytes()
            (source/'mcguide/example.md').write_text('updated')
            with patch.object(resources,'write_json',side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):resources.import_docs(source,root)
            self.assertEqual((root/'docs/LOCAL_MANIFEST.json').read_bytes(),previous)
            self.assertEqual((root/'docs/mcguide/example.md').read_bytes(),before)

    def test_stable_versions_are_numeric_and_offsite_beta_links_ignored(self):
        base='https://mc.163.com/dev/mcmanual/mc-dev/mcdocs/index.html'
        links=['1-ModAPI/更新信息/3.9.html','1-ModAPI/更新信息/3.10.html','1-ModAPI-beta/更新信息/4.0.html','https://elsewhere.invalid/dev/mcmanual/mc-dev/mcdocs/1-ModAPI/更新信息/99.0.html']
        self.assertEqual(sync.stable_versions(links,base),[(3,9),(3,10)])

    def test_version_check_is_read_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);source=docs_source(root/'incoming');resources.import_docs(source,root)
            before=(root/'docs/LOCAL_MANIFEST.json').read_bytes()
            result=sync.check_updates(root,lambda url:'<a href="1-ModAPI/更新信息/3.10.html">new</a>')
            self.assertEqual(result['status'],'UPDATE_AVAILABLE');self.assertEqual(result['written_files'],0)
            self.assertEqual((root/'docs/LOCAL_MANIFEST.json').read_bytes(),before)

    def test_unknown_navigation_does_not_claim_no_update(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            with self.assertRaises(resources.ResourceError):sync.check_updates(root,lambda url:'no links')


if __name__ == '__main__':
    unittest.main()
