"""S6-02: passing prototype evidence and explicit unresolved S6-01 gates."""
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]


class VectorGravity(unittest.TestCase):
    def setUp(self):
        self.evidence = json.loads((ROOT/'twin/vector/evidence.json').read_text())

    def test_prototype_evidence(self):
        self.assertTrue((ROOT/'docs/vector-gravity.md').is_file(), 'missing design note')
        self.assertTrue((ROOT/'patches/nbody-vector-gravity.patch').is_file(), 'missing opt-in patch')
        e = self.evidence
        self.assertEqual(e['macro_default'], 0)
        makefile = (ROOT/'mk/Makefile').read_text()
        self.assertIn('VECTOR_GRAVITY ?= 0', makefile)
        self.assertIn('CPPFLAGS += -DNBODY_VECTOR_GRAVITY=$(VECTOR_GRAVITY)', makefile)
        self.assertTrue(e['codegen']['masked_zmm_arithmetic'])
        self.assertEqual(e['exactness']['cases'], ['small-1', 'small-12', 'medium-1', 'medium-12', 'large-12'])
        self.assertTrue(e['exactness']['all_exact'])
        self.assertEqual(e['exactness']['acceleration_bytes'], 4096*24)
        self.assertTrue(e['exactness']['accelerations_exact'])
        self.assertEqual([x['first_body'] for x in e['groups']], [0, 1024])
        for group in e['groups']:
            self.assertIn('active_lanes_per_iteration', group)
            if group['scalar_functional'] != 'ok':
                self.assertEqual(group['comparison'], 'waiting for S14-37')
                self.assertNotIn('scalar_cycles_per_body', group)
        self.assertTrue((ROOT/'scripts/vector-card-commands.sh').is_file())

    @unittest.expectedFailure
    def test_twin_exactness_blocked_by_knc_twin_x87_double_rounding_gcc_knc_s14_37(self):
        """Blocker: knc-twin x87 double rounding (gcc-knc S14-37); group 0 mismatches."""
        for group in self.evidence['groups']:
            self.assertEqual(group['vector_functional'], 'ok')
            self.assertEqual(group['vector_simulate'], 'ok')

    @unittest.expectedFailure
    def test_full_vector_walk_blocked_by_open_gcc_knc_fp64_div_sqrt_correct_rounding(self):
        """Blocker: GCC-KNC FP64 div/sqrt rcp/rsqrt seeds + FMA rounding is open.

        Reported to the gcc-knc lead 2026-11-16. Until correct rounding is
        established, the strict prototype retains x87 sqrt/div/quad arithmetic.
        """
        self.assertTrue(self.evidence['codegen']['no_x87_arithmetic'],
                        'walk still contains x87 arithmetic')


if __name__ == '__main__':
    unittest.main()
