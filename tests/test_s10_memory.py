"""S10-07: one evidence test per acceptance deliverable."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10-memory'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class Memory(unittest.TestCase):
    def test_model_table(self):
        model = json.loads((B/'model.json').read_text())
        self.assertEqual(model['orders']['random']['targets'], model['orders']['spatial']['targets'])
        self.assertGreater(model['orders']['random']['lines_per_body'], 0)
        self.assertGreater(model['orders']['spatial']['lines_per_core_chunk'], 0)
        self.assertIn('Model table', (ROOT/'docs/research/s10-walk-memory.md').read_text())

    def test_twin(self):
        data = json.loads((B/'twin/evidence.json').read_text())
        self.assertTrue(data['model_table_used'])
        self.assertEqual(set(data['runs']), {'core-random', 'core-spatial', 'ring-random', 'ring-spatial'})
        for name, row in data['runs'].items():
            self.assertEqual(row['status'], 'ok', name)
            self.assertEqual(row['functional_check']['status'], 'ok', name)
            self.assertEqual(row['contexts'], 4 if name.startswith('core') else 32)
            self.assertEqual(row['binary_sha256'], sha(B/'card-base/milkyway_nbody.mic'))
            self.assertTrue(row['whole_function'])
            self.assertEqual(row['calls_per_context'], 2 if name.startswith('core') else 1)
            self.assertEqual(row['functional_check']['checked'], row['contexts']*row['calls_per_context'])

    def test_force_proof(self):
        data = json.loads((B/'proof.json').read_text())
        cases = ['small', 'medium', 'large', 'real-steps' if (ROOT/'workunits/real-steps').exists() else 'core-small']
        for case in cases:
            for variant in ('base', 'order', 'huge', 'both'):
                row = data['runs'][variant+'-'+case]
                run, ref = ROOT/row['run'], ROOT/row['reference']
                self.assertEqual(row['binary_sha256'], sha(B/('x86-'+variant+'/milkyway_nbody.exe')))
                self.assertEqual((run/'forces.bin').read_bytes(), (ref/'forces.bin').read_bytes())
                self.assertEqual((run/'forces.bin').stat().st_size, row['maps']*row['nbody']*24)
                self.assertEqual(compare.load_run(run), compare.load_run(ref))
                self.assertIn('PASS (strict absolute', row['compare'])

    def test_card_handoff(self):
        data = json.loads((B/'card-manifest.json').read_text())
        jobs = [s for s in (B/'window.sh').read_text().splitlines() if s.startswith('python tools/card_run ')]
        self.assertEqual(len(jobs), 9)
        case='real-steps' if (ROOT/'workunits/real-steps').exists() else 'core-small'
        self.assertEqual(sum('workunits/'+case+'/' in job for job in jobs),4)
        for job in jobs:
            self.assertIn('--threads 240', job)
            self.assertIn('--collect claude-stderr.txt', job)
            self.assertIn('scripts/s10-memory-launch.sh', job)
        for row in data['jobs']:
            binary = ROOT/row['binary']
            self.assertEqual(sha(binary), row['binary_sha256'])
            self.assertTrue(binary.read_bytes().startswith(b'\x7fELF'))
            self.assertIn('PASS: knc_lint exit 0', (binary.parent/'knc-lint.txt').read_text())
            options = (binary.parent/'.build-options').read_text()
            for setting in ('TREE_VARIANT=4', 'DF_REUSE=1', 'PARALLEL_QUAD=1', 'STATIC_INTEGRATE=1', 'VECTOR_GRAVITY=0', 'WALK_PROOF=0', 'PHASE_TIMERS=1'):
                self.assertIn('-DNBODY_'+setting, options)
            for key, value in [('WALK_ORDER', int(row['variant'] in ('order','both','pages'))), ('WALK_HUGEPAGES', int(row['variant'] in ('huge','both','pages')))]:
                self.assertIn('-DNBODY_%s=%d'%(key,value), options)
            self.assertTrue(row['prediction'])
            self.assertIn('-DNBODY_WALK_MEMORY_PROOF=%d'%int(row['variant']=='pages'), options)
            self.assertEqual(b'WALK_MEMORY name=' in binary.read_bytes(), row['variant']=='pages')
        self.assertEqual(len(data['release_binaries']), 4)
        for row in data['release_binaries']:
            binary=ROOT/row['binary']
            self.assertEqual(sha(binary), row['binary_sha256'])
            opts=(binary.parent/'.build-options').read_text()
            for setting in ('PHASE_TIMERS=0','TREE_VARIANT=4','DF_REUSE=1','PARALLEL_QUAD=1','STATIC_INTEGRATE=1','FORCE_CHUNK=4','VECTOR_GRAVITY=0','WALK_LAYOUT=0','WALK_MEMORY_PROOF=0','WALK_PROOF=0'):
                self.assertIn('-DNBODY_'+setting, opts)
            for key,value in [('WALK_ORDER',int(row['variant'] in ('order','both'))),('WALK_HUGEPAGES',int(row['variant'] in ('huge','both')))]:
                self.assertIn('-DNBODY_%s=%d'%(key,value),opts)
            self.assertIn('PASS: knc_lint exit 0', (binary.parent/'knc-lint.txt').read_text())
        for name, digest in data['files'].items():
            self.assertEqual(sha(ROOT/name), digest, name)

if __name__ == '__main__':
    unittest.main()
