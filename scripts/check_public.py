"""Check the public catalog and GET every NBM, verifying published SHA-256."""
import concurrent.futures
import hashlib
import json
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET


def get(url):
    for attempt in range(12):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'netbeans-cpp-preview-check'}), timeout=60) as response:
                return response.read()
        except Exception:
            if attempt == 11:
                raise
            time.sleep(5)


catalog_url = sys.argv[1]
catalog = ET.fromstring(get(catalog_url))
records = json.loads(get(urllib.parse.urljoin(catalog_url, 'build.json')))['packages']
expected = {r['file']: r['sha256'] for r in records}
modules = catalog.findall('.//module')
assert len(modules) >= 30


def check(module):
    url = urllib.parse.urljoin(catalog_url, module.attrib['distribution'])
    name = url.rsplit('/', 1)[-1]
    body = get(url)
    assert hashlib.sha256(body).hexdigest() == expected[name], name
    assert len(body) == int(module.attrib['downloadsize']), name
    return name


with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for name in pool.map(check, modules):
        print('PUBLIC DOWNLOAD PASS:', name)
print(f'PUBLIC CATALOG PASS: {catalog_url} ({len(modules)} packages)')
