"""Cache current official texts, import local texts or inspect formal-version navigation."""
import argparse
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit
import urllib.request

from resource_manager import ROOT, ResourceError, docs_status, import_docs, platform_baseline


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)


def stable_versions(links, base):
    versions = set()
    for href in links:
        parsed = urlsplit(urljoin(base, href))
        if parsed.scheme != 'https' or parsed.hostname != 'mc.163.com':
            continue
        match = re.fullmatch(r'/dev/mcmanual/mc-dev/mcdocs/1-ModAPI/更新信息/(\d+(?:\.\d+)+)\.html', unquote(parsed.path))
        if match:
            versions.add(tuple(map(int, match.group(1).split('.'))))
    return sorted(versions)


def check_updates(root=ROOT, fetch=None):
    sources = json.loads((Path(root) / 'docs/SOURCES.json').read_text(encoding='utf-8'))
    url = sources['stable_navigation']
    if fetch is None:
        from official_docs import OfficialHTTP
        fetch = OfficialHTTP()
        fetch.check_robots()
    content = fetch(url)
    parser = Links()
    parser.feed(content)
    versions = stable_versions(parser.links, url)
    if not versions:
        raise ResourceError('No formal-version links were found; update status is UNKNOWN')
    local = docs_status(root)
    local_versions = [tuple(map(int, version.split('.'))) for version in local.get('formal_versions', [])]
    latest = versions[-1]
    baseline = platform_baseline(root) or {}
    target = baseline.get('modsdk_version')
    return {'status': 'LOCAL_DOCS_NOT_INSTALLED' if not local_versions else 'UPDATE_AVAILABLE' if latest > max(local_versions) else 'NO_NEWER_FORMAL_VERSION_IN_NAVIGATION',
            'source': url, 'latest_navigation_version': '.'.join(map(str, latest)),
            'template_baseline_version': target,
            'template_update_status': 'UNKNOWN' if target is None else 'NEW_FORMAL_VERSION_REQUIRES_SYNC' if latest > tuple(map(int, target.split('.'))) else 'NO_NEWER_FORMAL_VERSION_IN_NAVIGATION',
            'local_document_versions': local.get('formal_versions', []), 'written_files': 0,
            'limits': 'Version navigation only; does not establish page freshness, offline-file availability or runtime support.'}


def check_offline_file(root=ROOT, fetch=None, head=None):
    """Discover the actual official button target; compare metadata without downloading the large archive."""
    sources = json.loads((Path(root) / 'docs/SOURCES.json').read_text(encoding='utf-8'))
    observed = sources.get('official_offline_download', {})
    page = observed.get('discovery_page')
    if not page or urlsplit(page).netloc != 'mc.163.com':
        raise ResourceError('Official offline-file discovery page is not configured')
    if fetch is None:
        from official_docs import OfficialHTTP
        fetch = OfficialHTTP()
        fetch.check_robots()
    content = fetch(page)
    matches = set(re.findall(r'https://g79\.gdl\.netease\.com/[A-Za-z0-9_./-]+\.zip', content))
    if len(matches) != 1:
        raise ResourceError('Official offline-file target is ambiguous or changed; inspect the official page')
    url = matches.pop()
    if head is None:
        class OfficialRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                parsed = urlsplit(newurl)
                if parsed.scheme != 'https' or parsed.netloc != 'g79.gdl.netease.com':
                    raise ResourceError('Official archive redirected outside its allowed origin')
                return super().redirect_request(req, fp, code, msg, headers, newurl)
        request = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'NeteaseWorkspaceLocalDocs/1.0'})
        with urllib.request.build_opener(OfficialRedirect()).open(request, timeout=20) as response:
            if urlsplit(response.url).scheme != 'https' or urlsplit(response.url).netloc != 'g79.gdl.netease.com':
                raise ResourceError('Official archive redirected outside its allowed origin')
            headers = dict(response.headers)
    else:
        headers = head(url)
    headers = {key.lower(): value for key, value in headers.items()}
    size = int(headers['content-length'])
    modified = parsedate_to_datetime(headers['last-modified']).date().isoformat()
    changed = url != observed.get('observed_url') or size != observed.get('bytes') or modified != observed.get('last_modified')
    return {'status': 'FILE_METADATA_CHANGED_INSPECT_FORMAL_VERSION' if changed else 'NO_CHANGED_FILE_SIGNATURE',
            'discovery_page': page, 'url': url, 'bytes': size, 'last_modified': modified,
            'downloaded_bytes': 0, 'limits': 'Metadata only; archive content/version must be checked before using a new formal file.'}


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--fetch', action='store_true', help='refresh public official article text for local reference; no images')
    group.add_argument('--check-updates', action='store_true')
    group.add_argument('--source', type=Path, help='local directory or ZIP containing document families; images are excluded')
    args = parser.parse_args(argv)
    try:
        if args.check_updates:
            try:
                result = check_updates(root)
            except Exception as error:
                result = {'status': 'UNKNOWN', 'template_update_status': 'UNKNOWN', 'reason': str(error), 'written_files': 0}
            try:
                result['official_offline_file'] = check_offline_file(root)
            except Exception as error:
                result['official_offline_file'] = {'status': 'UNKNOWN', 'reason': str(error)}
        elif args.fetch:
            from official_docs import fetch_official_docs
            result = fetch_official_docs(root, refresh=True)
        elif args.source:
            result = import_docs(args.source, root)
        else:
            print(json.dumps({'status': 'LOCAL_SOURCE_REQUIRED', 'reason': 'Select --fetch for official local-reference text acquisition, or --source for a local import.',
                              'next': 'Use official documentation or supply a permitted local source with --source.'}, ensure_ascii=False, indent=2))
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2 if (result.get('status') in ('PARTIAL', 'CORRUPT', 'LOCAL_DOCS_NOT_INSTALLED', 'UNKNOWN')
                     or result.get('template_update_status') == 'NEW_FORMAL_VERSION_REQUIRES_SYNC'
                     or result.get('official_offline_file', {}).get('status') == 'UNKNOWN') else 0
    except Exception as error:
        print(json.dumps({'status': 'ERROR', 'reason': str(error)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
