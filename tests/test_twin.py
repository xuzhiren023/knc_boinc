"""S1-03 acceptance: real results and a reproducible binary workflow."""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class TwinTest(unittest.TestCase):
    def test_documented_kernel_result(self):
        report = ROOT / 'docs/twin-check.md'
        self.assertTrue(report.is_file(), 'missing twin verdict')
        text = report.read_text()
        for command in ('validate', 'functional', 'simulate', 'bounds',
                        'hot/validate', 'hot/functional', 'hot/simulate', 'hot/bounds'):
            directory = ROOT / 'twin' / command
            self.assertTrue((directory / 'result.json').is_file(),
                            command + ' has not run on the compiled kernel')
            result = json.loads((directory / 'result.json').read_text())
            self.assertTrue((directory / 'summary.md').is_file())
            for key in ('status', 'result_class', 'assumptions', 'unsupported',
                        'limiting_constraints', 'calibration_status'):
                # Error envelopes omit fields such as result_class. The report
                # must distinguish an absent field from a returned null.
                value = result.get(key, '<absent>')
                self.assertIn(json.dumps(value, sort_keys=True), text)

    def test_binary_rerun_script(self):
        script = ROOT / 'twin/run.sh'
        self.assertTrue(script.is_file(), 'missing binary rerun script')
        text = script.read_text()
        for token in ('from_binary.py', '--function', '--init', 'capabilities',
                      'validate', 'functional', 'simulate', 'bounds',
                      'card-7120-measured'):
            self.assertIn(token, text)


if __name__ == '__main__':
    unittest.main()
