"""S5-02: every requested loop keeps its default and accepts an override."""
import pathlib
import re
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]


class ForceChunk(unittest.TestCase):
    def test_patch_and_build_selection(self):
        for name, element, kind, count in (
            ('grav', 'accels[0]', 'dynamic', 2),
            ('plain', 'accs[0]', 'dynamic', 2),
            ('shmem', 'Body', 'guided', 1),
        ):
            text = (ROOT / 'third_party/milkywayathome_client/nbody/src' /
                    ('nbody_' + name + '.c')).read_text()
            self.assertTrue('#ifndef NBODY_FORCE_CHUNK\n#define NBODY_FORCE_CHUNK (4096 / sizeof(' + element + '))\n#endif' in text,
                            name + ': missing overridable upstream default')
            self.assertEqual(len(re.findall(r'schedule\(' + kind + r', NBODY_FORCE_CHUNK\)', text)), count)
        makefile = (ROOT / 'mk/Makefile').read_text()
        self.assertIn('FORCE_CHUNK ?= 4', makefile)
        self.assertIn('CPPFLAGS += -DNBODY_FORCE_CHUNK=$(FORCE_CHUNK)', makefile)
        self.assertTrue((ROOT / 'patches/nbody-force-chunk.patch').is_file())


if __name__ == '__main__':
    unittest.main()
