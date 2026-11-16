"""S1-02 package and printed-command acceptance (build card before running)."""
import pathlib
import re
import shlex
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SHARED = pathlib.Path('C:/Users/xuzhi/Documents/gcc_knc/.work/_shared')
READELF = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-readelf.exe'

class CardTest(unittest.TestCase):
    def test_k1om_package(self):
        binary = ROOT / 'dist/card/milkyway_nbody.mic'
        self.assertTrue(binary.is_file(), 'make -C mk card must create the package')
        header = subprocess.check_output([str(READELF), '-h', str(binary)], text=True)
        self.assertIn('K1OM', header)
        dynamic = subprocess.check_output([str(READELF), '-d', str(binary)], text=True)
        self.assertRegex(dynamic, r'\[(?:\$ORIGIN:\$ORIGIN/\.\./lib)\]')
        objdump = SHARED / 'toolchain/cross/bin/k1om-mpss-linux-objdump.exe'
        init = subprocess.check_output([str(objdump), '-d', str(
            ROOT / 'build/card/crlibm/crlibm_private.c.o')], text=True)
        self.assertIn('<crlibm_init>', init)
        self.assertIn('$0x27f', init)
        self.assertIn('fldcw', init)
        # Recursively verify every compiler runtime dependency, never system glibc.
        pending, seen = [binary], set()
        runtime = SHARED / 'gcc-knc-16.2.0/k1om-mpss-linux/lib64'
        while pending:
            item = pending.pop()
            if item.name in seen:
                continue
            seen.add(item.name)
            output = subprocess.check_output([str(READELF), '-d', str(item)], text=True)
            for name in re.findall(r'\(NEEDED\).*\[([^]]+)\]', output):
                source = runtime / name
                # Cygwin symlinks are unreadable to native Windows Python.
                candidates = [p for p in runtime.glob(name + '.*')
                              if re.fullmatch(re.escape(name) + r'\.[0-9.]+', p.name)]
                if name == 'libgcc_s.so.1':
                    candidates = [source]
                if candidates:
                    source = max(candidates, key=lambda p: len(p.name))
                    staged = binary.parent / name
                    self.assertEqual(staged.read_bytes(), source.read_bytes())
                    pending.append(staged)
        import sys
        lint = subprocess.run([sys.executable, 'C:/Users/xuzhi/Documents/gcc_knc/tools/knc_lint', str(binary)], capture_output=True, text=True)
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)

    def test_printed_card_commands(self):
        result = subprocess.run(['C:/Program Files/Git/bin/bash.exe', 'scripts/card-check.sh'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [shlex.split(line) for line in result.stdout.splitlines() if line and not line.startswith('#')]
        self.assertEqual(len(commands), 4)
        for args, case, threads in zip(commands, ['small', 'small', 'medium', 'large'], ['240', '60', '240', '240']):
            self.assertEqual(args[:2], ['python', 'C:/Users/xuzhi/Documents/gcc_knc/tools/card_run'])
            self.assertIn('--print-histogram', args)
            self.assertIn('OMP_NUM_THREADS=' + threads, args)
            self.assertEqual(args[args.index('--threads') + 1], threads)
            staged = [args[i+1] for i, arg in enumerate(args) if arg == '--file']
            self.assertEqual(len(staged), len(set(pathlib.Path(p).name for p in staged)))
            self.assertIn('dist/card/milkyway_nbody.mic', staged)
            self.assertIn('workunits/' + case + '/params.lua', staged)
            self.assertIn('workunits/' + case + '/input.hist', staged)
            for runtime in (ROOT / 'dist/card').glob('*.so*'):
                self.assertIn('dist/card/' + runtime.name, staged)
            self.assertEqual(args[args.index('-f') + 1], 'params.lua')
            self.assertEqual(args[args.index('-h') + 1], 'input.hist')
