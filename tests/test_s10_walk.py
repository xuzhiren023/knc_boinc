"""S10-02 acceptance evidence (one check per ticket acceptance point)."""
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10-walk'
sys.path.insert(0, str(ROOT / 'scripts'))
import compare

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

class Walk(unittest.TestCase):
    def test_measurement_plan_and_profiles(self):
        self.assertIn('Model table', (ROOT/'docs/research/s10-force-walk.md').read_text(encoding='utf-8'))
        data = json.loads((B/'profiles.json').read_text(encoding='utf-8'))
        for variant in ('profile4', 'profile1', 'guided'):
            row = data[variant]
            self.assertGreater(row['maps'], 0)
            self.assertEqual(row['nodes'], data['profile4']['nodes'])
            self.assertEqual(row['interactions'], data['profile4']['interactions'])
            self.assertEqual(row['bodies'], data['profile4']['bodies'])
            self.assertEqual(row['threads'], 12)
            self.assertEqual(row['bodies'], 2220000)
            self.assertEqual(row['nodes'], 1087300798)
            self.assertEqual(row['interactions'], 892867454)
            self.assertGreater(row['max_mean_work'], 0)

    def test_assembly_and_compiler_items(self):
        data = json.loads((B/'assembly.json').read_text(encoding='utf-8'))
        self.assertGreater(data['functions']['nbGravity']['fxch'], 0)
        self.assertGreater(data['functions']['nbGravity']['stack_fp'], 0)
        self.assertGreater(data['functions']['nbGravity']['div'], 0)
        self.assertTrue((B/'compiler-repro-missed.txt').read_text(encoding='utf-8').strip())
        self.assertTrue((B/'compiler-repro.dis').read_text(encoding='utf-8').strip())

    def test_candidates_and_twin(self):
        data = json.loads((B/'twin/evidence.json').read_text(encoding='utf-8'))
        self.assertTrue(data['commands'])
        for variant in ('base', 'prefetch', 'hot', 'both'):
            row = data['variants'][variant]
            self.assertEqual(row['adapter_status'], 'ok')
            self.assertEqual(row['snapshot_sha256'], sha(B/('capture-'+variant+'.bin')))
            provenance=json.loads((B/('capture-'+variant+'-provenance.json')).read_text(encoding='utf-8'))
            self.assertEqual(provenance['binary_sha256'],sha(B/('x86-'+variant+'/milkyway_nbody.exe')))
            self.assertEqual(provenance['snapshot_sha256'],row['snapshot_sha256'])
            if row['status']=='ok':
                self.assertEqual(row['functional_check']['status'],'ok')
                self.assertEqual(row['functional_check']['checked'],4)
            self.assertIn(row['status'], ('ok', 'unsupported', 'budget_exhausted', 'invalid_input', 'missing_parameter', 'needs_parameters'))
        self.assertTrue((B/'host-ranking.json').exists())

    def test_binaries_window_and_predictions(self):
        manifest = json.loads((B/'card-manifest.json').read_text(encoding='utf-8'))
        jobs = [x for x in (B/'window.sh').read_text(encoding='utf-8').splitlines() if x.startswith('python tools/card_run ')]
        self.assertEqual(len(jobs), 8)
        self.assertEqual(sum('workunits/core-small/' in x for x in jobs), 1)
        for job in jobs:
            self.assertIn('--nthreads 240', job)
            self.assertIn('--threads 240', job)
            self.assertIn('--collect claude-stderr.txt', job)
            self.assertIn('scripts/s10-walk-launch.sh', job)
        for row in manifest['jobs']:
            binary = ROOT / row['binary']
            self.assertEqual(sha(binary), row['binary_sha256'])
            self.assertEqual(binary.read_bytes()[:4], b'\x7fELF')
            self.assertIn('PASS: knc_lint exit 0', (binary.parent/'knc-lint.txt').read_text(encoding='utf-8'))
            self.assertTrue(row['prediction'])
            opts = (binary.parent/'.build-options').read_text(encoding='utf-8')
            for x in ('TREE_VARIANT=4','VECTOR_GRAVITY=0','WALK_LAYOUT=0','FORCE_CHUNK=4',
                      'PARALLEL_QUAD=1','STATIC_INTEGRATE=1','DF_REUSE=0','PHASE_TIMERS=1','WALK_PROOF=0'):
                self.assertIn('-DNBODY_'+x, opts)
            v=row['variant']
            for key,value in dict(WALK_PREFETCH=int(v in ('prefetch','both')),
                    WALK_HOT=int(v in ('hot','both')),WALK_PROFILE=int(v in ('profile4','profile1','guided')),
                    WALK_SCHEDULE=1 if v=='profile1' else 2 if v=='guided' else 0).items():
                self.assertIn('-DNBODY_%s=%d'%(key,value),opts)
            self.assertIn('-O2',opts)
        for name, digest in manifest['files'].items():
            self.assertEqual(sha(ROOT/name), digest, name)

    def test_bit_identical_proof(self):
        data = json.loads((B/'proof.json').read_text(encoding='utf-8'))
        for variant in ('base','prefetch','hot','both','profile4','profile1','guided'):
            self.assertEqual(data['binaries'][variant], sha(B/('x86-'+variant+'/milkyway_nbody.exe')))
        required={'%s-%s-t%d'%(v,c,t) for v in ('prefetch','hot','both')
                  for c in ('small','medium','large') for t in (1,12)}
        required.update(v+'-large-t12' for v in ('base','profile4','profile1','guided'))
        self.assertTrue(required <= set(data['runs']))
        for row in data['runs'].values():
            run, ref = ROOT/row['run'], ROOT/row['reference']
            self.assertEqual(json.dumps(compare.load_run(run), sort_keys=True), json.dumps(compare.load_run(ref), sort_keys=True))
            self.assertEqual(row['force_sha256'], sha(run/'forces.bin'))
            self.assertEqual(row['force_sha256'], sha(ROOT/row['force_reference']))
            self.assertIn('PASS (strict absolute', row['compare'])

if __name__ == '__main__':
    unittest.main()
