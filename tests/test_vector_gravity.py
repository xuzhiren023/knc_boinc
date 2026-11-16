"""S6-01 acceptance: preserve every evidence requirement, including blockers."""
import json
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

class VectorGravity(unittest.TestCase):
    def test_ticket_evidence(self):
        self.assertTrue((ROOT/'docs/vector-gravity.md').is_file(), 'missing design note')
        self.assertTrue((ROOT/'patches/nbody-vector-gravity.patch').is_file(), 'missing opt-in patch')
        e = json.loads((ROOT/'twin/vector/evidence.json').read_text())
        self.assertTrue(e['codegen']['masked_zmm_arithmetic'])
        self.assertTrue(e['codegen']['no_x87_arithmetic'], 'walk still contains x87 arithmetic')
        self.assertEqual(e['exactness']['cases'], ['small-1', 'small-12', 'medium-1', 'medium-12', 'large-12'])
        self.assertTrue(e['exactness']['all_exact'])
        self.assertEqual(e['exactness']['acceleration_bytes'], 4096*24)
        self.assertTrue(e['exactness']['accelerations_exact'])
        self.assertEqual([x['first_body'] for x in e['groups']], [0, 1024])
        for group in e['groups']:
            self.assertEqual(group['vector_functional'], 'ok')
            self.assertEqual(group['vector_simulate'], 'ok')
            self.assertIn('active_lanes_per_iteration', group)
            if group['scalar_functional'] != 'ok':
                self.assertEqual(group['comparison'], 'waiting for S14-37')
                self.assertNotIn('scalar_cycles_per_body', group)
        self.assertTrue((ROOT/'scripts/vector-card-commands.sh').is_file())

if __name__ == '__main__':
    unittest.main()
