"""Build a self-contained update center from upstream NBM packages."""
import argparse
import copy
import datetime
import hashlib
import io
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile


def xml_bytes(root):
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    out = Path('site')
    out.mkdir(exist_ok=True)
    packages = sorted(Path('upstream/target/nbms').glob('*.nbm'))
    assert len(packages) >= 30, f'Incomplete CND build: {len(packages)} modules'
    catalog = ET.Element('module_updates', timestamp=datetime.datetime.now(datetime.timezone.utc).strftime('%S/%M/%H/%d/%m/%Y'))
    dependencies = []
    records = []
    for src in packages:
        with zipfile.ZipFile(src) as z:
            info = ET.fromstring(z.read('Info/info.xml'))
            manifest = info.find('manifest')
            assert manifest is not None
            cnb = manifest.get('OpenIDE-Module').split('/')[0]
            dependencies.append(manifest.get('OpenIDE-Module') + ' > ' + manifest.get('OpenIDE-Module-Specification-Version'))
            # The visible entry point installs the entire coherent module set.
            info.set('show-in-client', 'false')
            info.set('distribution', args.base_url.rstrip('/') + '/' + src.name)
            info.set('downloadsize', str(src.stat().st_size))
            catalog.append(info)
            # Fail on missing Class-Path extensions rather than publishing broken NBMs.
            for name in z.namelist():
                if name.startswith('netbeans/modules/') and name.endswith('.jar'):
                    with zipfile.ZipFile(io.BytesIO(z.read(name))) as jar:
                        raw = jar.read('META-INF/MANIFEST.MF').decode().replace('\r\n ', '').replace('\n ', '')
                        for line in raw.splitlines():
                            if line.startswith('Class-Path: '):
                                for rel in line[12:].split():
                                    target = str(Path(name).parent / rel)
                                    assert target in z.namelist(), f'{src.name}: missing {target}'
        shutil.copy2(src, out / src.name)
        records.append({'file': src.name, 'sha256': hashlib.sha256(src.read_bytes()).hexdigest(), 'module': cnb})

    cnb = 're.anas.netbeans.cpp'
    name = cnb.replace('.', '-')
    module_manifest = {
        'Manifest-Version': '1.0',
        'OpenIDE-Module': cnb,
        'OpenIDE-Module-Name': 'C/C++ Support for NetBeans 31',
        'OpenIDE-Module-Display-Category': 'C/C++',
        'OpenIDE-Module-Short-Description': 'C/C++ projects, editor, GCC/Clang toolchains and GDB integration.',
        'OpenIDE-Module-Specification-Version': args.version,
        'OpenIDE-Module-Module-Dependencies': ', '.join(dependencies),
        'AutoUpdate-Show-In-Client': 'true',
    }
    # Manifest lines are byte limited and continued with a leading space.
    lines = []
    for key, val in module_manifest.items():
        data = (key + ': ' + val).encode()
        while len(data) > 70:
            lines.append(data[:70]); data = b' ' + data[70:]
        lines.append(data)
    jar_data = io.BytesIO()
    with zipfile.ZipFile(jar_data, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', b'\r\n'.join(lines) + b'\r\n\r\n')
    info = ET.Element('module', codenamebase=cnb, distribution=args.base_url.rstrip('/') + '/' + name + '.nbm', downloadsize='0', needsrestart='true', targetcluster='cnd')
    manifest_attrs = {k: v for k, v in module_manifest.items() if k.startswith('OpenIDE-Module')}
    ET.SubElement(info, 'manifest', manifest_attrs)
    ET.SubElement(info, 'license', name='Apache-2.0').text = Path('upstream/LICENSE').read_text()
    config = '<?xml version="1.0"?><!DOCTYPE module PUBLIC "-//NetBeans//DTD Module Status 1.0//EN" "http://www.netbeans.org/dtds/module-status-1_0.dtd"><module name="' + cnb + '"><param name="autoload">false</param><param name="eager">false</param><param name="enabled">true</param><param name="jar">modules/' + name + '.jar</param><param name="reloadable">false</param></module>'
    path = out / (name + '.nbm')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('Info/info.xml', xml_bytes(info))
        z.writestr('netbeans/modules/' + name + '.jar', jar_data.getvalue())
        z.writestr('netbeans/config/Modules/' + name + '.xml', config)
    info.set('downloadsize', str(path.stat().st_size))
    catalog.append(info)
    (out / 'updates.xml').write_bytes(xml_bytes(catalog))
    records.append({'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'module': cnb})
    (out / 'build.json').write_text(json.dumps({'netbeans': '31', 'version': args.version, 'source': 'd6b3122946815b16b613449723b09cafc3a46036', 'packages': records}, indent=2))
    (out / 'SHA256SUMS').write_text(''.join(r['sha256'] + '  ' + r['file'] + '\n' for r in records))
    for filename in ['LICENSE', 'README.md']:
        shutil.copy2(Path('upstream') / filename, out / ('UPSTREAM-' + filename))
    print(f'Packaged {len(records)} modules')


if __name__ == '__main__':
    main()
