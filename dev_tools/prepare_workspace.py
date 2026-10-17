"""Inspect or prepare task resources without modifying global settings or launching tools."""
import argparse
import json
import os
from pathlib import Path
import sys

from resource_manager import ROOT, ResourceError, docs_status, import_docs, install_resource, registry, resource_status

TASKS = {'api': [], 'model': ['blockbench', 'modeling', 'attachable'], 'profile': ['tracy'],
         'pixel': ['pixel'], 'debug': ['modpc'], 'all': ['blockbench', 'modeling', 'attachable', 'tracy', 'pixel', 'modpc']}


def assess(root, task=None, selected=()):
    resources = registry(root)
    keys = list(dict.fromkeys(list(TASKS.get(task, [])) + list(selected)))
    unknown = set(keys) - set(resources)
    if unknown:
        raise ResourceError('Unknown resources: ' + ', '.join(sorted(unknown)))
    statuses = {key: resource_status(row, root) for key, row in resources.items()}
    docs = docs_status(root)
    missing = [key for key in keys if statuses[key]['status'] != 'READY']
    needs_docs = task in ('api', 'model', 'profile', 'pixel', 'debug', 'all')
    task_ready = not missing and (not needs_docs or docs['status'] == 'READY_LOCAL')
    return {'task': task, 'task_status': 'NOT_REQUESTED' if task is None and not selected else 'READY_RESOURCES' if task_ready else 'NOT_READY',
            'documents': docs, 'resources': statuses, 'required_tools_missing': missing,
            'api_contracts_verified': False, 'game_tested': False,
            'note': 'Resource readiness does not verify API contracts, dependency imports, MCP setup, GUI loading or game behavior.'}


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=TASKS)
    parser.add_argument('--tools', nargs='+', default=[])
    parser.add_argument('--fetch', action='store_true', help='fetch selected tools from pinned upstream versions for local use')
    parser.add_argument('--docs-source', type=Path, help='import a local document directory or ZIP; NETEASE_DOCS_SOURCE is also supported')
    parser.add_argument('--tool-source', action='append', default=[], metavar='ID=PATH', help='import pinned tool files from a local directory or ZIP')
    parser.add_argument('--fetch-docs', action='store_true', help='cache official current article text locally; never fetch images')
    parser.add_argument('--refresh-docs', action='store_true', help='refresh official article texts even when already present; requires --fetch-docs')
    parser.add_argument('--repair', action='store_true', help='replace modified selected tool payloads while preserving a local backup')
    parser.add_argument('--status', action='store_true', help='read-only; never imports, fetches or repairs')
    args = parser.parse_args(argv)
    try:
        if args.status and (args.fetch or args.docs_source or args.tool_source or args.repair or args.fetch_docs or args.refresh_docs):
            parser.error('--status cannot be combined with mutations')
        if args.repair and not (args.fetch or args.tool_source):
            parser.error('--repair needs --fetch or --tool-source')
        if args.fetch and not (args.task or args.tools or args.tool_source):
            parser.error('--fetch requires a task or explicit tool selection')
        if args.refresh_docs and not args.fetch_docs:
            parser.error('--refresh-docs requires --fetch-docs')
        if args.refresh_docs and args.docs_source:
            parser.error('--refresh-docs refreshes the official website; choose --docs-source separately for a local import')
        sources = {}
        for specification in args.tool_source:
            key, separator, value = specification.partition('=')
            if not separator or not value or key in sources:
                raise ResourceError('--tool-source requires unique ID=PATH values')
            sources[key] = Path(value)
        selected = list(dict.fromkeys(list(TASKS.get(args.task, [])) + args.tools + list(sources)))
        resources = registry(root)
        if set(selected) - set(resources):
            raise ResourceError('Unknown resource selection')
        operations, problems = [], []
        if not args.status:
            document_source = args.docs_source or (Path(os.environ['NETEASE_DOCS_SOURCE']) if os.environ.get('NETEASE_DOCS_SOURCE') and args.task and not args.refresh_docs else None)
            if document_source:
                try:
                    operations.append({'id': 'docs', 'result': import_docs(document_source, root)})
                except (OSError, ValueError, ResourceError) as error:
                    problems.append({'id': 'docs', 'reason': str(error)})
            if args.fetch_docs and not document_source:
                try:
                    from official_docs import fetch_official_docs
                    operations.append({'id': 'docs', 'result': fetch_official_docs(root, refresh=args.refresh_docs)})
                except Exception as error:
                    problems.append({'id': 'docs', 'reason': str(error)})
            for key in selected:
                source = sources.get(key)
                if key == 'modpc' and source is None and os.environ.get('NETEASE_MODPC_SOURCE'):
                    source = Path(os.environ['NETEASE_MODPC_SOURCE'])
                if not args.fetch and source is None:
                    continue
                try:
                    print('PREPARE ' + key, file=sys.stderr, flush=True)
                    operations.append(install_resource(resources[key], root, source=source, repair=args.repair))
                except Exception as error:
                    problems.append({'id': key, 'reason': str(error)})
        result = assess(root, args.task, selected)
        result['operations'] = operations
        result['problems'] = problems
        print(json.dumps(result, ensure_ascii=False, indent=2))
        partial_import = any(item.get('id') == 'docs' and item.get('result', {}).get('status') != 'READY_LOCAL' for item in operations)
        return 2 if problems or partial_import or result['task_status'] == 'NOT_READY' else 0
    except (OSError, ValueError, ResourceError) as error:
        print(json.dumps({'result': 'ERROR', 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
