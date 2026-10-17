"""Cache public official article text for local reference; never fetch image assets."""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from html import escape
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
import urllib.request
from urllib.robotparser import RobotFileParser

from resource_manager import ROOT, ResourceError, contained, docs_status, import_docs, write_json

ORIGIN = 'https://mc.163.com'
PREFIX = '/dev/mcmanual/mc-dev/'
USER_AGENT = 'NeteaseWorkspaceLocalDocs/1.0'
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


def official_page(href, base):
    parsed = urlsplit(urljoin(base, href))
    if parsed.scheme != 'https' or parsed.netloc != 'mc.163.com':
        return None
    path = unquote(parsed.path)
    if not path.startswith(PREFIX) or not path.endswith('.html'):
        return None
    relative = path[len(PREFIX):]
    if relative.split('/')[0] not in ('mcdocs', 'mcguide', 'mconline'):
        return None
    # Beta pages stay separate from the formal baseline and are not downloaded here.
    if any('beta' in part.lower() for part in relative.split('/')):
        return None
    try:
        contained(Path.cwd(), relative[:-5] + '.md')  # Reject unsafe Windows names and traversal.
    except ResourceError:
        return None
    return urlunsplit(('https', 'mc.163.com', quote(path, safe='/.-_'), '', ''))


class Article(HTMLParser):
    """Preserve article tables/code; omit executable nodes and embedded/remote images."""
    def __init__(self, url):
        super().__init__(convert_charrefs=False)
        self.url, self.links, self.parts = url, [], []
        self.depth = self.count = self.suppressed = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'):
            page = official_page(attrs['href'], self.url)
            if page:
                self.links.append(page)
        if tag == 'div' and 'theme-default-content' in attrs.get('class', '').split():
            self.count += 1
            self.depth = 1
            return
        if not self.depth:
            return
        if tag == 'div':
            self.depth += 1
        if tag in ('script', 'style', 'noscript', 'iframe', 'object', 'video', 'audio', 'svg'):
            self.suppressed += 1
        if self.suppressed:
            return
        if tag == 'img':
            self.parts.append('<span>[图片省略' + (': ' + escape(attrs['alt']) if attrs.get('alt') else '') + ']</span>')
            return
        safe = []
        for key in ('id', 'colspan', 'rowspan', 'title'):
            if key in attrs:
                safe.append((key, attrs[key]))
        if tag == 'a' and attrs.get('href'):
            href = urljoin(self.url, attrs['href'])
            if urlsplit(href).scheme in ('https', 'http'):
                safe.append(('href', href))
        self.parts.append('<' + tag + ''.join(' ' + k + '="' + escape(v, quote=True) + '"' for k, v in safe) + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag == 'div':
            self.depth -= 1
            if not self.depth:
                return
        if self.suppressed:
            if tag in ('script', 'style', 'noscript', 'iframe', 'object', 'video', 'audio', 'svg'):
                self.suppressed -= 1
            return
        if tag not in VOID:
            self.parts.append('</' + tag + '>')

    def handle_data(self, data):
        if self.depth and not self.suppressed:
            self.parts.append(escape(data))

    def handle_entityref(self, name):
        if self.depth and not self.suppressed:
            self.parts.append('&' + name + ';')

    def handle_charref(self, name):
        if self.depth and not self.suppressed:
            self.parts.append('&#' + name + ';')

    def body(self):
        content = ''.join(self.parts).strip()
        if self.count != 1 or not content or self.depth:
            raise ResourceError('Expected one complete official article: ' + self.url)
        return '<!-- source: ' + self.url + '\nformat: official article HTML; images omitted; local reference only -->\n\n' + content + '\n'


class OfficialHTTP:
    """Three workers share a request-start limit; no cookies, login or proxy bypass."""
    def __init__(self):
        self.lock, self.last_request = threading.Lock(), 0.0
        self.robots = None
        outer = self

        class Redirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                parsed = urlsplit(newurl)
                if parsed.scheme != 'https' or parsed.netloc != 'mc.163.com':
                    raise ResourceError('Official documentation redirected outside its allowed origin')
                if outer.robots and not outer.robots.can_fetch(USER_AGENT, newurl):
                    raise ResourceError('Redirect disallowed by robots.txt')
                return super().redirect_request(req, fp, code, msg, headers, newurl)

        self.opener = urllib.request.build_opener(Redirect())

    def __call__(self, url):
        parsed = urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'mc.163.com':
            raise ResourceError('Only the specified HTTPS official origin is allowed')
        if self.robots and not self.robots.can_fetch(USER_AGENT, url):
            raise ResourceError('Disallowed by official robots.txt: ' + url)
        for attempt in range(3):
            try:
                with self.lock:
                    time.sleep(max(0, 0.35 - (time.monotonic() - self.last_request)))
                    self.last_request = time.monotonic()
                req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/html,text/plain'})
                with self.opener.open(req, timeout=20) as response:
                    raw = response.read(4 * 1024 * 1024 + 1)
                    if len(raw) > 4 * 1024 * 1024:
                        raise ResourceError('Official page exceeds the text size limit')
                    return raw.decode('utf-8-sig')
            except HTTPError as error:
                if error.code not in (500, 502, 503, 504) or attempt == 2:
                    raise
            except (URLError, TimeoutError, ConnectionError):
                if attempt == 2:
                    raise
            time.sleep(2 ** (attempt + 1))

    def check_robots(self):
        try:
            content = self(ORIGIN + '/robots.txt')
        except HTTPError as error:
            if error.code != 404:
                raise
            content = ''
        robot = RobotFileParser(ORIGIN + '/robots.txt')
        robot.parse(content.splitlines())
        self.robots = robot


def fetch_official_docs(root=ROOT, refresh=False, fetch=None):
    root = Path(root)
    current = docs_status(root)
    if current['status'] == 'CORRUPT':
        raise ResourceError('Resolve changed local documents before fetching')
    if current['status'] == 'READY_LOCAL' and not refresh:
        return dict(current, acquisition='REUSED_LOCAL_TEXTS')
    sources = json.loads((root / 'docs/SOURCES.json').read_text(encoding='utf-8'))
    if not sources.get('auto_fetch') or sources.get('usage') != 'local-reference-only':
        raise ResourceError('Official local-reference acquisition is not configured')
    if fetch is None:
        fetch = OfficialHTTP()
        fetch.check_robots()
    pages = {}
    for seed in sources['navigation_seeds']:
        url = official_page(seed, seed)
        if url != seed:
            raise ResourceError('Invalid official navigation seed')
        parser = Article(url)
        parser.feed(fetch(url))
        pages[url] = parser.body()
        for link in parser.links:
            pages.setdefault(link, None)
    from sync_netease_docs_from_web import stable_versions
    versions = stable_versions(pages, sources['stable_navigation'])
    if not versions or len(pages) > 5000:
        raise ResourceError('Unrecognized formal navigation or excessive page count')
    if any(not any('/' + family + '/' in url for url in pages) for family in ('mcdocs', 'mcguide', 'mconline')):
        raise ResourceError('Official navigation does not cover all three document families')
    pending = [url for url, body in pages.items() if body is None]
    print('DOCS official text pages=' + str(len(pages)) + '; images=0', file=sys.stderr, flush=True)

    state = contained(root, 'dev_tools/local_state')
    state.mkdir(parents=True, exist_ok=True)
    cache_root = contained(root, 'dev_tools/local_state/official_doc_cache')
    cache_root.mkdir(parents=True, exist_ok=True)

    def read(url):
        cache = contained(cache_root, hashlib.sha256(url.encode()).hexdigest() + '.json')
        if not refresh and cache.is_file():
            try:
                cached = json.loads(cache.read_text(encoding='utf-8'))
            except (ValueError, OSError):
                cached = {}
            if (isinstance(cached, dict) and isinstance(cached.get('body'), str)
                    and isinstance(cached.get('fetched_at'), (float, int))
                    and cached.get('source') == url and 0 <= time.time() - cached['fetched_at'] < 21600
                    and hashlib.sha256(cached.get('body', '').encode()).hexdigest() == cached.get('sha256')):
                return url, cached['body']
        parser = Article(url)
        parser.feed(fetch(url))
        body = parser.body()
        write_json(cache, {'source': url, 'fetched_at': time.time(), 'body': body,
                          'sha256': hashlib.sha256(body.encode()).hexdigest()})
        return url, body

    # Stage every page before publishing; an error leaves the previous library untouched.
    with tempfile.TemporaryDirectory(prefix='official-docs-', dir=state) as temp:
        urls, count = {}, 0

        def save(url, body):
            nonlocal count
            name = unquote(urlsplit(url).path)[len(PREFIX):-5] + '.md'
            if name.casefold() in {item.casefold() for item in urls}:
                raise ResourceError('Official document paths collide')
            target = contained(Path(temp), name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8', newline='\n')
            urls[name] = url
            count += 1
            if count % 100 == 0:
                print('DOCS ' + str(count) + '/' + str(len(pages)), file=sys.stderr, flush=True)

        for url, body in pages.items():
            if body is not None:
                save(url, body)
        with ThreadPoolExecutor(max_workers=3) as pool:
            # Keep at most three in flight, without making slow pages stall a whole batch.
            queue = iter(pending)
            active = set()
            for _ in range(min(3, len(pending))):
                active.add(pool.submit(read, next(queue)))
            while active:
                done, active = wait(active, return_when=FIRST_COMPLETED)
                completed = [future.result() for future in done]
                for url, body in completed:
                    save(url, body)
                for _ in completed:
                    url = next(queue, None)
                    if url is not None:
                        active.add(pool.submit(read, url))
        result = import_docs(Path(temp), root, source_info={'source_kind': 'official-web-texts', 'source': ORIGIN + PREFIX,
                            'navigation_latest_formal_version': '.'.join(map(str, versions[-1])), 'source_urls': urls})
    return dict(result, acquisition='OFFICIAL_TEXTS_CACHED', images_downloaded=0, navigation_pages=len(pages))
