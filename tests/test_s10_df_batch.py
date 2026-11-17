"""One S10-10 offline acceptance point; native likelihood is explicitly gated."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
B = ROOT / 'build/s10/df-batch'
sys.path.insert(0, str(ROOT/'scripts'))
import compare
from importlib import import_module
old = import_module('s10-df-special')
def read(name):
    return json.loads((B/name).read_text())
class Acceptance(unittest.TestCase):
    def test_batched_setup_handoff(self):
        unit = read('kernel.json')
        for key in ['integrals_bitwise', 'max_decisions_bitwise', 'rng_order_exact', 'limit_exact', 'fallback_exact', 'schedule_coverage']:
            self.assertTrue(unit[key], key)
        proof = read('proof.json')
        for case, count in [('core-small',4000),('real-steps',20000)]:
            row = proof[case]
            a,b = [ROOT/row[k] for k in ['reference','experiment']]
            self.assertEqual((a/'initial-bodies.bin').stat().st_size, 56*count)
            if case=='core-small':
                self.assertEqual(hashlib.sha256((a/'initial-bodies.bin').read_bytes()).hexdigest(),'7117b750caad318ab42a781346ca480a9f43fa1828e0832b58ad06fc00b88b59')
            self.assertEqual(old.file_differences(a/'initial-bodies.bin',b/'initial-bodies.bin',56),(0,None))
            self.assertEqual(old.file_differences(a/'rng.bin',b/'rng.bin',row['rng_record_bytes']),(0,None))
            self.assertEqual(compare.load_run(a)[0].hex(), compare.load_run(b)[0].hex())
            self.assertEqual(row['threads'],4)
            stats=row['counts']
            self.assertEqual(stats['evaluated'],stats['used']+stats['wasted'])
            self.assertGreaterEqual(stats['max_batch'],8)
            self.assertGreater(stats['wasted'],0)
            self.assertEqual(sum(row['attempt_histogram'].values()),count)
            self.assertEqual(sum(int(k)*v for k,v in row['attempt_histogram'].items()),stats['attempts'])
            self.assertEqual(sum(row['batch_histogram'].values()),stats['batches'])
        model=read('working-set.json')
        self.assertLess(model['node_bytes_per_core'],32768)
        self.assertLess(model['total_budget_bytes_per_core'],32768)
        self.assertGreater(model['local_node_stack_bytes'],0)
        self.assertGreater(model['local_worker_stack_bytes'],0)
        twin=read('twin-results.json')
        self.assertEqual(set(twin['independent_integrals']),{'1','2','4'})
        self.assertTrue(twin['commands'])
        for row in twin['independent_integrals'].values():
            self.assertIn(row['status'],['ok','unsupported','blocked'])
            if row['status']!='ok': self.assertIsNone(row['cycles_per_node'])
        handoff=read('handoff.json')
        self.assertTrue(read('prediction.json')['recorded_utc'])
        for name,digest in handoff['files'].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
        for v in ['release','batch']:
            folder=B/('card-'+v)
            binary=(folder/'milkyway_nbody.mic').read_bytes()
            self.assertEqual(binary[:4],b'\x7fELF')
            self.assertNotIn(b'DFB_COUNTS',binary)
            self.assertNotIn(b'S10_RNG_TRACE',binary)
            self.assertIn('PASS: knc_lint exit 0',(folder/'knc-lint.txt').read_text())
            options=(folder/'.build-options').read_text()
            self.assertIn('-DNBODY_TREE_VARIANT=4',options)
            self.assertIn('-DNBODY_DF_BATCH='+('1' if v=='batch' else '0'),options)
            if v=='batch':
                for option in ['DF_SPECIAL','DF_VECTOR8','DF_VECTOR8_GUARD','DF_VECTOR8_SCALAR_LOG_ATAN']:
                    self.assertIn('-DNBODY_'+option+'=1',options)
        provenance=read('library-provenance.json')
        self.assertEqual(provenance['installed_card'],provenance['snapshot_card'])
        script=(B/'card-window.sh').read_text()
        self.assertEqual(script.count('--transfer tcp-large'),4)
        self.assertIn('GOMP_CPU_AFFINITY=',script)
        self.assertIn('prediction.json',script)
    def test_native_likelihood(self):
        folder=ROOT/'runs/card/s10-df-batch'
        required=[folder/(v+'-'+c+'-240.json') for c in ['core-small','real-steps'] for v in ['release','batch']]
        if not all(p.exists() for p in required) and os.environ.get('S10_REQUIRE_CARD')!='1':
            self.skipTest('Lead card jobs pending; --card requires native likelihood equality')
        for case in ['core-small','real-steps']:
            values=[]
            for v in ['release','batch']:
                name=v+'-'+case+'-240'
                self.assertEqual(json.loads((folder/(name+'.json')).read_text())['exit_code'],0)
                values.append(compare.load_run(folder/(name+'.txt'))[0].hex())
            self.assertEqual(*values)
if __name__=='__main__': unittest.main()
