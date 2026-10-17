"""Version follow-up, document refresh precedence and first-use failure reporting."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_workspace as prepare
import resource_manager as resources
import sync_netease_docs_from_web as sync
import verify_local_environment as verify
from test_maintenance_tools import docs_source, fixture, record, save

TOOLS = Path(__file__).resolve().parents[1]


def baseline(root, version='3.9'):
    data = json.loads((TOOLS.parent/'docs/PLATFORM_BASELINE.json').read_text(encoding='utf-8'))
    data['modsdk_version'] = version
    data['official_release_notes'] = data['official_release_notes'].rsplit('/',1)[0]+'/'+version+'.html'
    save(root/'docs/PLATFORM_BASELINE.json', data)


class ReviewTests(unittest.TestCase):
    def test_workspace_edit_is_reported_but_published_source_stays_strict(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); fixture(root)
            (root/'README.md').write_text('My workspace',encoding='utf-8')
            self.assertEqual(verify.verify(root,profile='workspace')['result'],'PASS')
            self.assertEqual(verify.verify(root,profile='workspace')['workspace_edits'],['README.md'])
            self.assertEqual(verify.verify(root)['result'],'FAIL')

    def test_workspace_profile_still_rejects_modified_scripts_and_invalid_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary); fixture(root)
            path=root/'dev_tools/helper.py';path.write_text('original=1\n')
            manifest=json.loads((root/'dev_tools/manifests/distribution_manifest.json').read_text())
            manifest['files'].append(record('dev_tools/helper.py',path.read_bytes()))
            save(root/'dev_tools/manifests/distribution_manifest.json',manifest)
            path.write_text('changed=2\n')
            save(root/'components/catalog.json',{'components':'wrong'})
            failures=verify.verify(root,profile='workspace')['failures']
            self.assertTrue(any('HASH_MISMATCH' in item for item in failures))
            self.assertTrue(any('INVALID_WORKSPACE_METADATA' in item for item in failures))

    def test_full_alias_keeps_strict_hashes_when_workspace_profile_is_also_requested(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            (root/'README.md').write_text('Workspace edit',encoding='utf-8')
            result=verify.verify(root,full=True,profile='workspace')
            self.assertEqual(result['profile'],'full')
            self.assertIn('HASH_MISMATCH: README.md',result['failures'])

    def test_new_formal_version_requests_baseline_sync_using_numeric_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);baseline(root)
            page='<a href="/dev/mcmanual/mc-dev/mcdocs/1-ModAPI/更新信息/3.10.html?catalog=1">正式</a>'
            result=sync.check_updates(root,fetch=lambda _:page)
            self.assertEqual(result['template_update_status'],'NEW_FORMAL_VERSION_REQUIRES_SYNC')
            self.assertEqual(result['template_baseline_version'],'3.9')

    def test_baseline_rejects_mismatched_release_note_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root);baseline(root)
            data=json.loads((root/'docs/PLATFORM_BASELINE.json').read_text())
            data['modsdk_version']='3.10';save(root/'docs/PLATFORM_BASELINE.json',data)
            with self.assertRaises(resources.ResourceError):resources.platform_baseline(root)

    def test_offline_file_check_runs_even_if_version_navigation_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            with patch.object(sync,'check_updates',side_effect=OSError('offline')), patch.object(sync,'check_offline_file',return_value={'status':'NO_CHANGED_FILE_SIGNATURE'}) as offline:
                with contextlib.redirect_stdout(io.StringIO()): code=sync.main(['--check-updates'],root)
                self.assertEqual(code,2);offline.assert_called_once_with(root)

    def test_explicit_refresh_ignores_old_environment_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            with patch.dict(os.environ,{'NETEASE_DOCS_SOURCE':str(root/'old')}), patch.object(prepare,'import_docs',side_effect=AssertionError('old source')), patch('official_docs.fetch_official_docs',return_value={'status':'READY_LOCAL'}) as remote:
                with contextlib.redirect_stdout(io.StringIO()):prepare.main(['--task','api','--fetch-docs','--refresh-docs'],root)
                remote.assert_called_once_with(root,refresh=True)

    def test_refresh_and_explicit_local_import_are_not_silently_combined(self):
        with tempfile.TemporaryDirectory() as temporary:
            with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                prepare.main(['--fetch-docs','--refresh-docs','--docs-source',temporary],Path(temporary))

    def test_older_full_document_source_cannot_downgrade_current_api_texts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);fixture(root)
            current=docs_source(root/'current');resources.import_docs(current,root)
            old=docs_source(root/'old');(old/'mcdocs/1-ModAPI/更新信息/3.9.md').rename(old/'mcdocs/1-ModAPI/更新信息/2.4.md')
            (old/'mcdocs/1-ModAPI/接口/example.md').write_text('Old API',encoding='utf-8')
            before=(root/'docs/LOCAL_MANIFEST.json').read_bytes()
            with self.assertRaisesRegex(resources.ResourceError,'Older formal'):resources.import_docs(old,root)
            self.assertEqual((root/'docs/LOCAL_MANIFEST.json').read_bytes(),before)
            self.assertNotEqual((root/'docs/mcdocs/1-ModAPI/接口/example.md').read_text(encoding='utf-8'),'Old API')


class BootstrapTests(unittest.TestCase):
    def run_bootstrap(self, root, dependency_failure=False, newer=False, shell_override=None):
        shell=shell_override or shutil.which('pwsh') or shutil.which('powershell')
        if not shell:self.skipTest('PowerShell unavailable')
        tools=root/'dev_tools';tools.mkdir(parents=True)
        shutil.copyfile(TOOLS/'bootstrap_workspace.ps1',tools/'bootstrap_workspace.ps1')
        stubs={
            'verify_local_environment.py':{'result':'PASS','workspace_edits':['components/catalog.json']},
            'prepare_workspace.py':{'task_status':'READY_RESOURCES','documents':{'status':'READY_LOCAL'},'resources':{'modpc':{'status':'READY'},'tracy':{'status':'READY'},'pixel':{'status':'READY'}},'problems':[]},
            'sync_netease_docs_from_web.py':{'status':'NO_NEWER_FORMAL_VERSION_IN_NAVIGATION','template_update_status':'NEW_FORMAL_VERSION_REQUIRES_SYNC' if newer else 'NO_NEWER_FORMAL_VERSION_IN_NAVIGATION','official_offline_file':{'status':'NO_CHANGED_FILE_SIGNATURE'}}}
        for name,data in stubs.items():
            (tools/name).write_text('import json, sys\n'+("print('PREPARE fixture',file=sys.stderr)\n" if name=='prepare_workspace.py' else '')+'print(json.dumps('+repr(data)+'))\n',encoding='utf-8')
        (tools/'setup_python.ps1').write_text("throw 'Dependency fixture failure'\n",encoding='utf-8')
        save(tools/'local_state/FIRST_USE_REPORT.json',{'result':'READY_RESOURCES','dependencies':'PASS','attempt_id':'old'})
        command=[shell,'-NoProfile','-NonInteractive']
        if Path(shell).name.lower()=='powershell.exe':
            command.extend(['-ExecutionPolicy','RemoteSigned'])  # local test process only; does not override Group Policy
        command.extend(['-File',str(tools/'bootstrap_workspace.ps1'),'-Python',sys.executable])
        if not dependency_failure:command.append('-ResourcesOnly')
        run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45)
        report=json.loads((tools/'local_state/FIRST_USE_REPORT.json').read_text(encoding='utf-8-sig'))
        return run,report

    def test_failed_dependency_attempt_replaces_previous_success_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            run,report=self.run_bootstrap(Path(temporary),dependency_failure=True)
            self.assertEqual(run.returncode,1,run.stderr)
            self.assertEqual(report['result'],'FAIL')
            self.assertEqual(report['failed_stage'],'dependencies')
            self.assertEqual(report['dependencies'],'FAIL')
            self.assertNotEqual(report['attempt_id'],'old')

    def test_confirmed_resource_preparation_completes_without_extra_prompt(self):
        with tempfile.TemporaryDirectory() as temporary:
            run,report=self.run_bootstrap(Path(temporary))
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(report['result'],'READY_RESOURCES')
            self.assertEqual(report['workspace_edits'],['components/catalog.json'])
            self.assertFalse(report['game_tested'])

    def test_windows_powershell_accepts_normal_native_progress_on_stderr(self):
        shell=shutil.which('powershell')
        if not shell:self.skipTest('Windows PowerShell unavailable')
        with tempfile.TemporaryDirectory() as temporary:
            run,report=self.run_bootstrap(Path(temporary),shell_override=shell)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertEqual(report['result'],'READY_RESOURCES')

    def test_newer_formal_version_is_reported_after_resources_are_prepared(self):
        with tempfile.TemporaryDirectory() as temporary:
            run,report=self.run_bootstrap(Path(temporary),newer=True)
            self.assertEqual(run.returncode,2,run.stderr)
            self.assertEqual(report['result'],'ATTENTION_REQUIRED')
            self.assertEqual(report['resources'],'READY_RESOURCES')


if __name__=='__main__':unittest.main()
