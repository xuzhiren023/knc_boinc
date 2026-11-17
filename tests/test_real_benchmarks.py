"""Offline acceptance checks; never launch a benchmark or contact the card."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import compare


class RealBenchmarks(unittest.TestCase):
    def test_case(self):
        original = (ROOT / 'workunits/core-small/params.lua').read_text()
        expected = original.replace('totalBodies           = 4000', 'totalBodies           = 20000')
        expected = expected.replace('totalLightBodies      = 364', 'totalLightBodies      = 1818')
        expected = expected.replace('Core-small regression', 'Real-steps benchmark').replace('32 steps', '128 steps')
        expected = expected.replace('evolveTime = 32 *', 'evolveTime = 128 *')
        case = ROOT / 'workunits/real-steps'
        self.assertEqual((case / 'params.lua').read_text(), expected)
        self.assertEqual((case / 'OCS_data_2025_north_194.hist').read_bytes(),
                         (ROOT / 'workunits/core-small/OCS_data_2025_north_194.hist').read_bytes())

    def test_references(self):
        base = ROOT / 'tests/references/real-benchmarks'
        for case in ('core-small', 'real-steps'):
            best, stock = [base / (case + '-' + variant) for variant in ('release', 'stock')]
            self.assertEqual(compare.load_run(best), compare.load_run(stock))
            for run in (best, stock):
                info = json.loads((run / 'measurement.json').read_text())
                self.assertEqual(info['returncode'], 0)
                self.assertEqual(info['threads'], 12)
                self.assertGreater(info['wall_seconds'], 0)
        info = json.loads((base / '117676-release/measurement.json').read_text())
        self.assertEqual(info['phases']['steps']['calls'], 1568)
        self.assertGreater(info['phases']['whole_run']['seconds'], 0)

    def test_documentation(self):
        text = (ROOT / 'docs/benchmarks.md').read_text()
        for word in ('core-small', 'real-steps', '117676', 'large', 'small', 'medium', '47.95', '1,673'):
            self.assertIn(word, text)

    def test_window(self):
        text = (ROOT / 'scripts/real-benchmark-window.sh').read_text()
        self.assertIn('tools/card_run', text)
        self.assertIn('S10-01/build/s10/card-release-timers', text)
        self.assertIn('core-small real-steps', text)
        self.assertNotIn('workunits/large', text)
        for runtime in ('libgcc_s.so.1', 'libgomp.so.1', 'libstdc++.so.6'):
            self.assertIn(runtime, text)


if __name__ == '__main__':
    unittest.main()
