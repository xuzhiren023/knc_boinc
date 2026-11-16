"""S7-01: the build and BOINC package must identify standard N-body 1.96."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '1e640779f1cabf88aaa49e4db569cfe7e09016c4'


class Nbody196(unittest.TestCase):
    def test_standard_app_pin(self):
        fetch = (ROOT / 'scripts/fetch.sh').read_text()
        self.assertIn('tag=nbody_1.96\n', fetch)
        self.assertIn('commit=' + COMMIT, fetch)
        self.assertIn('dest=third_party/milkywayathome_client_196\n', fetch)
        self.assertIn('UPSTREAM := $(ROOT)/third_party/milkywayathome_client_196\n',
                      (ROOT / 'mk/Makefile').read_text())
        config = (ROOT / 'config/nbody_config.h').read_text()
        self.assertIn('#define NBODY_VERSION_MINOR 96\n', config)
        self.assertIn('#define NBODY_VERSION       "1.96"', config)
        self.assertIn(COMMIT, (ROOT / 'config/milkyway_git_version.h').read_text())
        self.assertIn('`nbody_1.96`', (ROOT / 'SOURCES.md').read_text())
        for name in ('packaging/make_package.sh', 'packaging/check_package.py'):
            text = (ROOT / name).read_text()
            self.assertIn("('version_num', '196')", text)
            self.assertIn("('platform', 'windows_x86_64')", text)
            self.assertIn("('app_name', 'milkyway_nbody')", text)


if __name__ == '__main__':
    unittest.main()
