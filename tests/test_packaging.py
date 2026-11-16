"""One package acceptance test, including checker rejection cases."""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'dist/milkyway_package'
CHECKER = ROOT / 'packaging/check_package.py'


def check(path, ok):
    result = subprocess.run([sys.executable, str(CHECKER), str(path)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert (result.returncode == 0) == ok, result.stdout
    return result.stdout.strip()


def test_package():
    print(check(PACKAGE, True))
    required = {'knc_wrapper.exe', 'knc_wrapper.cfg.example', 'milkyway_nbody.mic',
                'cygwin1.dll', 'cyggcc_s-seh-1.dll', 'cygstdc++-6.dll',
                'cygiconv-2.dll', 'cygintl-8.dll'}
    assert required <= {p.name for p in PACKAGE.iterdir()}
    assert (ROOT / 'docs/packaging.md').is_file()
    tree = ET.parse(PACKAGE / 'app_info.xml')
    assert tree.findtext('app/name') == 'milkyway_nbody'
    assert len(tree.findall('app_version')) == 1
    assert tree.findtext('app_version/avg_ncpus') == '1'
    assert tree.findtext('app_version/max_ncpus') == '1'
    assert tree.findtext('app_version/version_num') == '197'
    # Isolate deliberate corruption; never modify the deliverable.
    with tempfile.TemporaryDirectory(dir=str(ROOT / 'build/tmp')) as scratch:
        copy = pathlib.Path(scratch) / 'package'
        mutations = ('missing_file', 'wrong_case', 'main_program', 'dangling_ref',
                     'duplicate_name', 'unreferenced_file', 'unsafe_name')
        for mutation in mutations:
            shutil.copytree(PACKAGE, copy)
            xml = copy / 'app_info.xml'
            t = ET.parse(xml)
            r = t.getroot()
            if mutation == 'missing_file':
                (copy / 'cygwin1.dll').unlink()
            elif mutation == 'wrong_case':
                (copy / 'cygwin1.dll').rename(copy / 'CYGWIN1.dll')
            elif mutation == 'main_program':
                for ref in r.findall('app_version/file_ref'):
                    marker = ref.find('main_program')
                    if marker is not None:
                        ref.remove(marker)
            elif mutation == 'dangling_ref':
                r.find('app_version/file_ref/file_name').text = 'absent.exe'
            elif mutation == 'duplicate_name':
                ET.SubElement(r, 'file_info').append(ET.fromstring('<name>knc_wrapper.exe</name>'))
            elif mutation == 'unreferenced_file':
                (copy / 'extra.dll').write_bytes(b'extra')
            else:
                r.find('file_info/name').text = '../escape'
            t.write(xml)
            check(copy, False)
            shutil.rmtree(copy)
    print('PASS packaging acceptance (real build, inventory, XML, checker rejection cases)')


if __name__ == '__main__':
    test_package()
