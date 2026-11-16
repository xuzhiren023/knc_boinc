"""S6-03: full vector walk, host bytes, and the remaining scalar twin blocker."""
import json
from pathlib import Path
import unittest
import tempfile
import sys
ROOT = Path(__file__).resolve().parents[1]


class VectorGravity(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT/'twin/vector/evidence.json').read_text())

    def test_full_vector_walk(self):
        e = self.evidence['codegen']
        self.assertTrue(e['no_x87_arithmetic'], 'walk still contains x87 arithmetic')
        self.assertTrue(e['masked_zmm_arithmetic'])
        self.assertTrue(e['literal_full_vector_requirement_met'])
        self.assertTrue(e['final_extraction_matches_executed_kernel'])
        for op in ('vrcp23ps', 'vrsqrt23ps'):
            self.assertGreater(e['opcode_counts'].get(op, 0), 0)
        self.assertTrue((ROOT/'patches/nbody-vector-gravity.patch').is_file())
        self.assertIn('VECTOR_GRAVITY ?= 0', (ROOT/'mk/Makefile').read_text())
        self.assertEqual(self.evidence['macro_default'], 0)

    def test_x86_exactness(self):
        e = self.evidence['exactness']
        self.assertEqual(e['cases'], ['small-1', 'small-12', 'medium-1', 'medium-12', 'large-12'])
        self.assertTrue(e['all_exact'])
        self.assertEqual(e['acceleration_bytes'], 4096*24)
        self.assertTrue(e['accelerations_exact'])

    def test_twin_capabilities_and_four_groups(self):
        e = self.evidence
        self.assertTrue(e['capabilities']['required_functional_support'])
        self.assertEqual([x['first_body'] for x in e['groups']], [0, 1024, 2048, 4088])
        for group in e['groups']:
            self.assertIn('active_lanes_per_iteration', group)
            self.assertEqual(group['vector_functional'], 'ok')
            self.assertEqual(group['vector_simulate'], 'ok')
            self.assertGreater(group['vector_cycles_per_body'], 0)
            self.assertEqual(group['vector_functional_evidence']['functional_check']['checked'], 9)

    @unittest.expectedFailure
    def test_scalar_comparison_blocked_by_knc_twin_x87_double_rounding_s14_37(self):
        """Blocker: installed twin 0.4.0 still has x87 double rounding (S14-37)."""
        for group in self.evidence['groups']:
            self.assertEqual(group['scalar_functional'], 'ok')
            self.assertIn('scalar_cycles_per_body', group)

    def test_card_handoff_and_range_limits(self):
        doc = (ROOT/'docs/vector-gravity.md').read_text()
        self.assertIn('DBL_MAX', doc)
        command = (ROOT/'scripts/vector-card-commands.sh').read_text()
        self.assertIn('--threads 240', command)
        self.assertIn('check_vector_card.py', command)
        self.assertEqual(self.evidence['exactness']['range_audit']['nonfinite_results'], 0)
        sys.path.insert(0, str(ROOT/'scripts'))
        from check_vector_card import scientific_tokens
        (ROOT/'build/tmp').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'build/tmp') as tmp:
            a, b = Path(tmp)/'a.txt', Path(tmp)/'b.txt'
            text = """<search_likelihood>-12.5</search_likelihood>
<histogram>
n = 1
lambdaBins = 1
betaBins = 1
1 0 0 0.25 0.01 0 -1 0 -1
</histogram>
"""
            a.write_text(text); b.write_text(text)
            self.assertEqual(scientific_tokens(a), scientific_tokens(b))
            # Below numeric tolerance: exact checks must still reject it.
            b.write_text(text.replace('-12.5', '-12.500000000001'))
            self.assertNotEqual(scientific_tokens(a), scientific_tokens(b))
            b.write_text(text.replace('0.25', '0.250000000001'))
            self.assertNotEqual(scientific_tokens(a), scientific_tokens(b))


if __name__ == '__main__':
    unittest.main()
