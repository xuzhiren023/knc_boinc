import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class CompareTest(unittest.TestCase):
    def test_accept_identical_and_reject_doctored_output(self):
        (ROOT / 'build' / 'tmp').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build' / 'tmp') as tmp:
            a, b = pathlib.Path(tmp) / 'a', pathlib.Path(tmp) / 'b'
            for path in (a, b):
                path.mkdir()
                (path / 'stdout.txt').write_text('<search_likelihood>-12.5</search_likelihood>\n')
                (path / 'histogram.txt').write_text(
                    '# Generated timestamp is not science data\n<histogram>\n'
                    'n = 4\nmassPerParticle = 0.5\ntotalSimulated = 4\n'
                    'lambdaBins = 2\nbetaBins = 1\n'
                    '1 0 0 0.25 0.01 0 -1 0 -1\n'
                    '1 1 0 0.75 0.02 0 -1 0 -1\n</histogram>\n')
            def compare():
                return subprocess.run([sys.executable, str(ROOT / 'scripts' / 'compare.py'), str(a), str(b)], capture_output=True, text=True)
            result = compare()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS', result.stdout)
            (b / 'histogram.txt').write_text(
                (a / 'histogram.txt').read_text().replace('0.25', '0.5'))
            result = compare()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('max_abs=0.25', result.stdout)
            # A captured stream is sufficient: no remote result files needed.
            stream = pathlib.Path(tmp) / 'card.txt'
            # Standalone upstream omits the BOINC-only <histogram> wrappers.
            stream.write_text('OpenMP diagnostic\n' + (b / 'stdout.txt').read_text()
                              + (b / 'histogram.txt').read_text().replace('<histogram>', '').replace('</histogram>', '')
                              + 'run complete\n')
            captured = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'compare.py'), str(a), str(stream)], capture_output=True, text=True)
            self.assertEqual(captured.returncode, 0, captured.stdout + captured.stderr)
            # Restore the histogram, then corrupt the other scientific result.
            (b / 'histogram.txt').write_bytes((a / 'histogram.txt').read_bytes())
            (b / 'stdout.txt').write_text('<search_likelihood>-12.4</search_likelihood>\n')
            result = compare()
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('FAIL', result.stdout)
            # Incomplete/non-finite runs must never silently pass.
            for output in ('', '<search_likelihood>nan</search_likelihood>\n'):
                (b / 'stdout.txt').write_text(output)
                result = compare()
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn('FAIL', result.stderr)
