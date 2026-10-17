"""Export only verified public core files; local documents, tools and state are excluded."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import uuid
import zipfile

from resource_manager import ROOT, ResourceError, contained
from verify_local_environment import verify


def export(root, destination, overwrite=False):
    root = Path(root).resolve()
    destination = Path(destination).resolve()
    if destination.exists() and not overwrite:
        raise ResourceError('Export already exists; choose another path or use --overwrite')
    result = verify(root, profile='source')
    if result['result'] != 'PASS':
        raise ResourceError('Source verification failed; refusing export')
    manifest_path = root/'dev_tools/manifests/distribution_manifest.json'
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    names = {row['path'] for row in manifest['files']}
    forbidden = ('docs/mcdocs/', 'docs/mcguide/', 'docs/mconline/', 'dev_tools/external/',
                 'dev_tools/python_env/', 'dev_tools/local_state/', 'dev_tools/backups/')
    if any(name.startswith(forbidden) or name == 'docs/LOCAL_MANIFEST.json' for name in names):
        raise ResourceError('The public manifest contains a local-only payload')
    if 'dev_tools/manifests/distribution_manifest.json' in names:
        raise ResourceError('The distribution manifest must not contain itself')
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name+'.'+uuid.uuid4().hex+'.part')
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as package:
            for row in manifest['files']:
                content = contained(root, row['path']).read_bytes()
                if hashlib.sha256(content).hexdigest() != row['sha256']:
                    raise ResourceError('Core changed during export: '+row['path'])
                package.writestr(row['path'], content)
            package.writestr('dev_tools/manifests/distribution_manifest.json', manifest_bytes)
        with zipfile.ZipFile(temporary) as package:
            if package.testzip() is not None or len(package.namelist()) != len(set(package.namelist())):
                raise ResourceError('ZIP integrity check failed')
        os.replace(str(temporary), str(destination))
    finally:
        if temporary.exists():
            temporary.unlink()
    return {'result':'PASS', 'files':len(manifest['files'])+1, 'bytes':destination.stat().st_size,
            'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(), 'scope':'public-core-only'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args=parser.parse_args()
    try:
        print(json.dumps(export(ROOT,args.out,args.overwrite),ensure_ascii=False,indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'result':'ERROR','reason':str(error)},ensure_ascii=False))
        return 1


if __name__=='__main__':
    sys.exit(main())
