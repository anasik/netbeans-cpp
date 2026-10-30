"""Install through Plugin Manager, restart, then test inside NetBeans."""
from pathlib import Path
import os
import subprocess
import zipfile

root = Path.cwd()
nb = root / 'netbeans'
user = root / 'test-userdir'
logs = root / 'verification'
logs.mkdir(exist_ok=True)
catalog = (root / 'site/updates.xml').as_uri()
# Test the exact local files before publishing; release URLs are immutable.
import xml.etree.ElementTree as ET
tree = ET.parse(root / 'site/updates.xml')
for m in tree.getroot().findall('module'):
    m.set('distribution', (root / 'site' / m.get('distribution').rsplit('/', 1)[-1]).as_uri())
test_catalog = root / 'test-updates.xml'
tree.write(test_catalog, encoding='utf-8', xml_declaration=True)
cmd = [str(nb / 'bin/netbeans'), '--nosplash', '--nogui', '--userdir', str(user), '--cachedir', str(root / 'test-cache'), '-J-Dnetbeans.logger.console=true']
with (logs / 'install.log').open('w') as out:
    subprocess.run(cmd + ['--modules', '--extra-uc', test_catalog.as_uri(), '--install', 're.anas.netbeans.cpp', '-J-Dnetbeans.close=true'], stdout=out, stderr=subprocess.STDOUT, check=True, timeout=240)

# A test-only module, installed after the normal update-center transaction.
classes = root / 'probe-classes'
classes.mkdir(exist_ok=True)
classpath = os.pathsep.join(str(p) for p in nb.rglob('*.jar'))
subprocess.run(['javac', '-proc:none', '-cp', classpath, '-d', str(classes), 'tests/Probe.java'], check=True)
manifest = 'Manifest-Version: 1.0\nOpenIDE-Module: re.anas.cppcheck\nOpenIDE-Module-Specification-Version: 1.0\nOpenIDE-Module-Install: re/anas/cppcheck/Probe.class\nOpenIDE-Module-Module-Dependencies: org.openide.modules > 7.0,\n org.openide.util > 9.0, org.openide.util.lookup > 8.0,\n org.openide.filesystems > 9.0, org.openide.loaders > 7.0,\n org.openide.nodes > 7.0, org.netbeans.modules.projectapi > 1.0\n\n'
(user / 'modules').mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(user / 'modules/re-anas-cppcheck.jar', 'w') as z:
    z.writestr('META-INF/MANIFEST.MF', manifest)
    for p in classes.rglob('*.class'):
        z.write(p, p.relative_to(classes))
(user / 'config/Modules').mkdir(parents=True, exist_ok=True)
(user / 'config/Modules/re-anas-cppcheck.xml').write_text('<?xml version="1.0"?><!DOCTYPE module PUBLIC "-//NetBeans//DTD Module Status 1.0//EN" "http://www.netbeans.org/dtds/module-status-1_0.dtd"><module name="re.anas.cppcheck"><param name="autoload">false</param><param name="eager">false</param><param name="enabled">true</param><param name="jar">modules/re-anas-cppcheck.jar</param><param name="reloadable">false</param></module>')
with (logs / 'runtime.log').open('w') as out:
    subprocess.run(cmd + ['-J-Dcpp.fixture=' + str(root / 'cpp-fixture'), '-J-Dcpp.report=' + str(logs / 'result.txt')], stdout=out, stderr=subprocess.STDOUT, check=True, timeout=240)
assert (logs / 'result.txt').is_file(), 'Runtime probe did not complete'
print((logs / 'result.txt').read_text())
