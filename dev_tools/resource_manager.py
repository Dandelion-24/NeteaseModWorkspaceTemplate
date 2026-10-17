"""Pinned local resources. Standard library only; importing this module does not write."""
import hashlib
from datetime import date
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import tempfile
import time
import urllib.request
from urllib.parse import unquote, urlsplit
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOC_FAMILIES = ('mcdocs', 'mcguide', 'mconline')
TEXT_SUFFIXES = {'.md', '.txt', '.html', '.htm', '.rst'}
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024


class ResourceError(RuntimeError):
    pass


def platform_baseline(root=ROOT):
    path = Path(root) / 'docs/PLATFORM_BASELINE.json'
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('channel') != 'formal':
        raise ResourceError('Platform baseline must describe a formal release')
    version = data.get('modsdk_version', '')
    if not isinstance(version, str) or not re.fullmatch(r'\d+(?:\.\d+)+', version):
        raise ResourceError('Platform baseline needs a numeric ModSDK version')
    bedrock = data.get('bedrock_version')
    if not isinstance(bedrock, list) or len(bedrock) != 3 or any(type(n) is not int or n < 0 for n in bedrock):
        raise ResourceError('Platform baseline needs a three-integer Bedrock version')
    if type(data.get('manifest_format_version')) is not int or data['manifest_format_version'] < 1:
        raise ResourceError('Platform baseline needs a positive numeric Manifest format')
    if not re.fullmatch(r'\d+(?:\.\d+)+', str(data.get('game_python_version', ''))):
        raise ResourceError('Platform baseline needs the verified game Python version')
    try:
        date.fromisoformat(data.get('checked_on', ''))
    except (ValueError, TypeError) as error:
        raise ResourceError('Platform baseline needs a valid verification date') from error
    source = urlsplit(data.get('official_release_notes', ''))
    if (source.scheme != 'https' or source.netloc != 'mc.163.com'
            or unquote(source.path) != '/dev/mcmanual/mc-dev/mcdocs/1-ModAPI/更新信息/' + version + '.html'):
        raise ResourceError('Platform baseline release-note source must match its formal ModSDK version')
    return data


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def relative_name(value):
    if not isinstance(value, str) or not value or '\\' in value or '\x00' in value:
        raise ResourceError('Invalid relative path')
    path = PurePosixPath(value)
    if path.is_absolute() or PureWindowsPath(value).drive or any(part in ('', '.', '..') for part in value.split('/')):
        raise ResourceError('Unsafe relative path: ' + value)
    # Windows strips trailing spaces/dots and reserves device names and ADS syntax.
    for part in path.parts:
        if ':' in part or part.endswith((' ', '.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', part):
            raise ResourceError('Unsafe Windows path: ' + value)
    return path.as_posix()


def is_redirect(path):
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)
    except FileNotFoundError:
        return False


def contained(root, relative):
    relative = relative_name(relative)
    root = Path(root).resolve()
    target = root / relative
    if not target.resolve().is_relative_to(root):
        raise ResourceError('Path escapes its root: ' + relative)
    cursor = target
    while cursor != root:
        if is_redirect(cursor):
            raise ResourceError('Resource paths cannot contain links: ' + relative)
        cursor = cursor.parent
    return target


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def registry(root=ROOT):
    data = json.loads((Path(root) / 'dev_tools/manifests/resources.json').read_text(encoding='utf-8'))
    result = {}
    for row in data['resources']:
        if not re.fullmatch(r'[a-z][a-z0-9_-]*', row['id']) or row['id'] in result:
            raise ResourceError('Invalid or repeated resource ID')
        if not relative_name(row['destination']).startswith('dev_tools/external/'):
            raise ResourceError('Tool destination must be inside dev_tools/external')
        seen = set()
        for file_row in row['files']:
            name = relative_name(file_row['path'])
            if name.casefold() in seen or not re.fullmatch(r'[a-f0-9]{64}', file_row['sha256']):
                raise ResourceError('Invalid resource file record')
            seen.add(name.casefold())
        if row['primary'] not in {item['path'] for item in row['files']}:
            raise ResourceError('Primary entry is not in the pinned file list')
        result[row['id']] = row
    return result


def resource_status(row, root=ROOT):
    target = contained(root, row['destination'])
    if target.exists() and not target.is_dir():
        raise ResourceError('Tool destination is not a directory: ' + row['destination'])
    missing, changed = [], []
    for file_row in row['files']:
        path = contained(target, file_row['path'])
        if not path.is_file():
            missing.append(file_row['path'])
        elif path.stat().st_size != file_row['bytes'] or sha256(path) != file_row['sha256']:
            changed.append(file_row['path'])
    status = 'CORRUPT' if changed else 'ABSENT' if len(missing) == len(row['files']) else 'INCOMPLETE' if missing else 'READY'
    return {'id': row['id'], 'status': status, 'missing': missing, 'changed': changed,
            'auto_fetch': row['auto_fetch'], 'license_status': row['license']['status']}


def download(url, destination, expected_bytes=None, timeout=30):
    if not url.startswith('https://'):
        raise ResourceError('Only HTTPS downloads are allowed')
    started = time.monotonic()
    request = urllib.request.Request(url, headers={'User-Agent': 'Netease-Workspace-Template'})
    total = 0
    with urllib.request.urlopen(request, timeout=timeout) as response, Path(destination).open('wb') as stream:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > (expected_bytes if expected_bytes is not None else MAX_ARCHIVE_BYTES):
                raise ResourceError('Download exceeds expected size')
            if time.monotonic() - started > 240:
                raise ResourceError('Download exceeded its time limit')
            stream.write(chunk)
    if expected_bytes is not None and total != expected_bytes:
        raise ResourceError('Download is incomplete')


def zip_members(package):
    members = []
    seen = set()
    total = 0
    for item in package.infolist():
        name = item.filename.rstrip('/')
        if not name:
            continue
        relative_name(name)
        if stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1:
            raise ResourceError('Linked or encrypted ZIP members are not supported')
        if name.casefold() in seen:
            raise ResourceError('Duplicate ZIP path: ' + name)
        seen.add(name.casefold())
        total += item.file_size
        if total > MAX_ARCHIVE_BYTES or len(seen) > 50000:
            raise ResourceError('Archive exceeds its extraction limit')
        if not item.is_dir():
            members.append((name, item))
    return members


def extract_tool(archive, payload, row):
    with zipfile.ZipFile(archive) as package:
        members = zip_members(package)
        roots = {name.split('/')[0] for name, _ in members}
        if len(roots) != 1 or any('/' not in name for name, _ in members):
            raise ResourceError('Pinned source archive must have one enclosing directory')
        mapped = {name.split('/', 1)[1]: item for name, item in members}
        additional = {item['path'] for item in row.get('additional_downloads', [])}
        if set(mapped) != {item['path'] for item in row['files']} - additional:
            raise ResourceError('Archive contents differ from the pinned file list')
        for name, item in mapped.items():
            path = contained(payload, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with package.open(item) as source, path.open('wb') as destination:
                shutil.copyfileobj(source, destination)


def validate_payload(payload, records):
    for row in records:
        path = contained(payload, row['path'])
        if not path.is_file() or path.stat().st_size != row['bytes'] or sha256(path) != row['sha256']:
            raise ResourceError('Pinned file verification failed: ' + row['path'])


def remote_allowed(row):
    if not row.get('auto_fetch'):
        return False
    if row['license']['status'] == 'verified':
        return True
    basis = row.get('local_use_basis', {})
    return (row['id'] == 'modpc' and basis.get('kind') == 'upstream-installation-instructions'
            and basis.get('redistribution_granted') is False
            and basis.get('source') == 'https://github.com/MCNeteaseDevs/ModPC-MCP-Tool/blob/' + row.get('revision', '') + '/README.md')


def install_resource(row, root=ROOT, source=None, repair=False, downloader=download):
    root = Path(root).resolve()
    status = resource_status(row, root)
    if status['status'] == 'READY':
        return {'id': row['id'], 'status': 'ALREADY_PRESENT'}
    if status['status'] == 'CORRUPT' and not repair:
        raise ResourceError('Existing files differ; inspect them before using --repair: ' + row['id'])
    if source is None and not remote_allowed(row):
        raise ResourceError('MANUAL_SOURCE_REQUIRED: ' + row['id'] + '; see the upstream terms and supply a local source')
    state = contained(root, 'dev_tools/local_state')
    state.mkdir(parents=True, exist_ok=True)
    target = contained(root, row['destination'])
    with tempfile.TemporaryDirectory(prefix='install-', dir=state) as temp:
        temporary = Path(temp)
        payload = temporary / 'payload'
        payload.mkdir()
        if source is not None and Path(source).is_dir():
            for record in row['files']:
                original = contained(Path(source), record['path'])
                destination = contained(payload, record['path'])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(original, destination)
        elif row['kind'] == 'zip':
            archive = temporary / 'source.zip'
            if source is None:
                downloader(row['url'], archive, row['download_bytes'])
            else:
                shutil.copyfile(source, archive)
            if sha256(archive) != row['archive_sha256']:
                raise ResourceError('Source archive hash mismatch: ' + row['id'])
            extract_tool(archive, payload, row)
            for record in row.get('additional_downloads', []):
                destination = contained(payload, record['path'])
                destination.parent.mkdir(parents=True, exist_ok=True)
                downloader(record['url'], destination, record['bytes'])
        else:
            if source is not None:
                raise ResourceError('This resource requires a directory containing all pinned files')
            for record in row['files']:
                destination = contained(payload, record['path'])
                destination.parent.mkdir(parents=True, exist_ok=True)
                downloader(record['url'], destination, record['bytes'])
        validate_payload(payload, row['files'])
        target.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if target.exists():
            backup = contained(root, 'dev_tools/local_state/backups/' + row['id'] + '-' + uuid.uuid4().hex)
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(target), str(backup))
        try:
            os.replace(str(payload), str(target))
        except Exception:
            if backup is not None:
                os.replace(str(backup), str(target))
            raise
    return {'id': row['id'], 'status': 'INSTALLED', 'source': 'local-import' if source is not None else 'pinned-upstream',
            'previous_copy_preserved': backup is not None}


def docs_status(root=ROOT):
    root = Path(root)
    manifest = contained(root, 'docs/LOCAL_MANIFEST.json')
    if not manifest.is_file():
        return {'status': 'NOT_INSTALLED', 'files': 0, 'missing_families': list(DOC_FAMILIES), 'api_contracts_verified': False}
    data = json.loads(manifest.read_text(encoding='utf-8'))
    records = data.get('files', [])
    if not records:
        raise ResourceError('Local document manifest has no files')
    families = set()
    failures = []
    for row in records:
        name = relative_name(row['path'])
        if name.split('/')[0] not in DOC_FAMILIES or Path(name).suffix.lower() not in TEXT_SUFFIXES:
            raise ResourceError('Unexpected document payload path')
        path = contained(root / 'docs', name)
        if not path.is_file() or sha256(path) != row['sha256']:
            failures.append(name)
        if name.startswith('mcdocs/1-ModAPI/') or name.split('/')[0] in ('mcguide', 'mconline'):
            families.add(name.split('/')[0])
    missing = sorted(set(DOC_FAMILIES) - families)
    return {'status': 'CORRUPT' if failures else 'PARTIAL' if missing else 'READY_LOCAL', 'files': len(records),
            'missing_families': missing, 'changed_or_missing': failures, 'formal_versions': data.get('formal_versions', []),
            'scope': 'Imported text files only; not a claim of a complete or current official mirror', 'api_contracts_verified': False}


def import_docs(source, root=ROOT, source_info=None):
    root = Path(root).resolve()
    source = Path(source).resolve()
    state = contained(root, 'dev_tools/local_state')
    state.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='docs-', dir=state) as temp:
        payload = Path(temp) / 'payload'
        payload.mkdir()
        records = []
        if source.is_dir():
            candidates = [path for path in (source, source / 'docs') if any((path / family).is_dir() for family in DOC_FAMILIES)]
            if len(candidates) != 1:
                raise ResourceError('Choose a directory containing mcdocs, mcguide and/or mconline')
            base = candidates[0]
            for family in DOC_FAMILIES:
                folder = base / family
                if not folder.is_dir():
                    continue
                if is_redirect(folder):
                    raise ResourceError('Document families cannot be links')
                for path in folder.rglob('*'):
                    if is_redirect(path):
                        raise ResourceError('Document source contains a link')
                    if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                        name = path.relative_to(base).as_posix()
                        target = contained(payload, name)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(path, target)
                        records.append({'path': name, 'bytes': target.stat().st_size, 'sha256': sha256(target)})
        elif source.is_file() and zipfile.is_zipfile(source):
            with zipfile.ZipFile(source) as package:
                members = zip_members(package)
                prefixes = set()
                for name, _ in members:
                    parts = name.split('/')
                    for index, part in enumerate(parts[:-1]):
                        if part in DOC_FAMILIES:
                            prefixes.add(tuple(parts[:index]))
                            break
                if len(prefixes) != 1:
                    raise ResourceError('Document archive has ambiguous or missing document roots')
                prefix = next(iter(prefixes))
                for name, item in members:
                    parts = name.split('/')
                    if tuple(parts[:len(prefix)]) != prefix:
                        continue
                    parts = parts[len(prefix):]
                    if len(parts) < 2 or parts[0] not in DOC_FAMILIES or Path(parts[-1]).suffix.lower() not in TEXT_SUFFIXES:
                        continue
                    name = '/'.join(parts)
                    target = contained(payload, name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with package.open(item) as original, target.open('wb') as destination:
                        shutil.copyfileobj(original, destination)
                    records.append({'path': name, 'bytes': target.stat().st_size, 'sha256': sha256(target)})
        else:
            raise ResourceError('Document source must be a local directory or ZIP')
        if not records:
            raise ResourceError('No supported text documents found; nothing was changed')
        for row in records:
            if source_info and row['path'] in source_info.get('source_urls', {}):
                row['source_url'] = source_info['source_urls'][row['path']]
        seen_names = set()
        for row in records:
            name = row['path']
            if name.casefold() in seen_names:
                raise ResourceError('Document paths collide: ' + name)
            seen_names.add(name.casefold())
            try:
                contained(payload, name).read_bytes().decode('utf-8-sig')
            except UnicodeDecodeError as error:
                raise ResourceError('Document must be readable UTF-8 text: ' + name) from error
        # A refresh preserves earlier pages not present in the incoming source.
        previous = contained(root, 'docs/LOCAL_MANIFEST.json')
        old = json.loads(previous.read_text(encoding='utf-8')) if previous.is_file() else {'files': []}
        if previous.is_file() and docs_status(root)['status'] == 'CORRUPT':
            raise ResourceError('Existing local documents changed; resolve them before refreshing')
        incoming_versions = [tuple(map(int, match.group(1).split('.'))) for row in records
                             for match in [re.search(r'^mcdocs/1-ModAPI/更新信息/(\d+(?:\.\d+)+)\.', row['path'])] if match]
        existing_versions = [tuple(map(int, version.split('.'))) for version in old.get('formal_versions', [])]
        if incoming_versions and existing_versions and max(incoming_versions) < max(existing_versions):
            raise ResourceError('Older formal documentation source refused; existing texts were preserved')
        combined = {row['path']: row for row in old.get('files', [])}
        unchanged = set()
        for row in records:
            if row['path'] in combined:
                current = contained(root / 'docs', row['path'])
                if not current.is_file() or sha256(current) != combined[row['path']]['sha256']:
                    raise ResourceError('Existing local document changed; resolve it before refreshing: ' + row['path'])
                if combined[row['path']]['sha256'] == row['sha256']:
                    unchanged.add(row['path'])
            combined[row['path']] = row
        if previous.is_file() and len(unchanged) == len(records):
            return docs_status(root)
        docs_root = root / 'docs'
        backup = state / 'backups' / ('docs-' + uuid.uuid4().hex)
        changed = []
        manifest_bytes = previous.read_bytes() if previous.is_file() else None
        try:
            for row in records:
                if row['path'] in unchanged:
                    continue
                target = contained(docs_root, row['path'])
                if target.is_file():
                    saved = contained(backup, row['path'])
                    saved.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(target, saved)
                target.parent.mkdir(parents=True, exist_ok=True)
                changed.append((row['path'], target.is_file()))
                os.replace(str(contained(payload, row['path'])), str(target))
            versions = sorted({match.group(1) for name in combined for match in [re.search(r'^mcdocs/1-ModAPI/更新信息/(\d+(?:\.\d+)+)\.', name)] if match}, key=lambda v: tuple(map(int, v.split('.'))))
            write_json(previous, {'schema_version': 1, 'source_kind': (source_info or {}).get('source_kind', 'user-local-import'),
                                  'source': (source_info or {}).get('source', str(source)),
                                  'navigation_latest_formal_version': (source_info or {}).get('navigation_latest_formal_version'),
                                  'imported_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'distribution': 'local-only',
                                  'formal_versions': versions, 'files': sorted(combined.values(), key=lambda row: row['path'])})
        except Exception:
            for name, existed in reversed(changed):
                target = contained(docs_root, name)
                if existed:
                    shutil.copyfile(contained(backup, name), target)
                elif target.is_file():
                    target.unlink()
            if manifest_bytes is not None:
                previous.write_bytes(manifest_bytes)
            elif previous.exists():
                previous.unlink()
            raise
    return docs_status(root)
