"""Read-only source integrity and task resource readiness; standard library only."""
import argparse
import json
from pathlib import Path
import sys

from prepare_workspace import TASKS, assess
from resource_manager import ROOT, ResourceError, contained, platform_baseline, registry, remote_allowed, sha256


def workspace_editable(name):
    return name.endswith(('.md', '.yaml')) or name in ('components/catalog.json', 'docs/PLATFORM_BASELINE.json')


def verify(root, full=False, profile='source', task=None):
    root = Path(root).resolve()
    if full:
        profile = 'full'
    failures = []
    workspace_edits = []
    manifest = json.loads((root / 'dev_tools/manifests/distribution_manifest.json').read_text(encoding='utf-8'))
    seen = set()
    for row in manifest['files']:
        name = row['path']
        if name in seen:
            failures.append('DUPLICATE_RECORD: ' + name)
            continue
        seen.add(name)
        try:
            path = contained(root, name)
            if not path.is_file():
                failures.append('MISSING_CORE: ' + name)
            elif sha256(path) != row['sha256']:
                if profile == 'workspace' and workspace_editable(name):
                    workspace_edits.append(name)
                else:
                    failures.append('HASH_MISMATCH: ' + name)
        except ResourceError as error:
            failures.append(str(error))
    for name in ('components/catalog.json', 'docs/PLATFORM_BASELINE.json'):
        path = root / name
        if path.is_file():
            try:
                data = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    raise ValueError('expected a JSON object')
                if name.endswith('catalog.json') and not isinstance(data.get('components'), list):
                    raise ValueError('components must be a list')
                if name.endswith('PLATFORM_BASELINE.json'):
                    platform_baseline(root)
            except (ValueError, TypeError, ResourceError) as error:
                failures.append('INVALID_WORKSPACE_METADATA: ' + name + ': ' + str(error))
    readiness = assess(root, task)
    for key, status in readiness['resources'].items():
        if task and key not in TASKS[task]:
            continue
        if status['status'] in ('CORRUPT', 'INCOMPLETE'):
            failures.append('INSTALLED_RESOURCE_' + status['status'] + ': ' + key)
    if readiness['documents']['status'] == 'CORRUPT':
        failures.append('LOCAL_DOCUMENTS_CORRUPT')
    sources = json.loads((root / 'docs/SOURCES.json').read_text(encoding='utf-8'))
    if sources.get('auto_fetch') and sources.get('usage') != 'local-reference-only':
        failures.append('DOCUMENT_ACQUISITION_MUST_BE_LOCAL_REFERENCE_ONLY')
    for key, row in registry(root).items():
        if row['auto_fetch'] and not remote_allowed(row):
            failures.append('UNVERIFIED_TOOL_MUST_NOT_AUTO_FETCH: ' + key)
    if full or profile == 'full':
        for key, status in readiness['resources'].items():
            if status['status'] != 'READY':
                failures.append('FULL_RESOURCE_NOT_READY: ' + key)
        if readiness['documents']['status'] != 'READY_LOCAL':
            failures.append('FULL_DOCUMENTS_NOT_READY')
    result = 'FAIL' if failures else 'NOT_READY' if readiness['task_status'] == 'NOT_READY' else 'PASS'
    return {'result': result, 'profile': 'full' if full else profile, 'files_hashed': len(seen),
            'failures': failures, 'readiness': readiness,
            'workspace_edits': workspace_edits,
            'scope': 'Source/full profiles verify published hashes. Workspace profile lists editable document/catalog/baseline changes while retaining script and resource checks. Task readiness and game acceptance are separate.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('source', 'workspace', 'full'), default='source')
    parser.add_argument('--full', action='store_true', help='compatibility alias for --profile full; requires local documents and every tool')
    parser.add_argument('--task', choices=TASKS, help='also require the resources used by this task')
    args = parser.parse_args(argv)
    try:
        result = verify(ROOT, args.full, args.profile, args.task)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['failures'] else 2 if result['result'] == 'NOT_READY' else 0
    except (OSError, ValueError, ResourceError) as error:
        print(json.dumps({'result': 'ERROR', 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
