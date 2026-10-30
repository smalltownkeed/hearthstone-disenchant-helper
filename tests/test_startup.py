import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

@unittest.skipUnless(os.name == 'nt', 'Windows launcher')
class StartupTests(unittest.TestCase):
    def test_incomplete_offline_bundle_exits_without_network_or_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copy(Path(__file__).resolve().parents[1] / 'launch.py', root / 'launch.py')
            done = subprocess.run([sys.executable, str(root / 'launch.py'), '--check'],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=10)
            self.assertEqual(done.returncode, 1)
            self.assertTrue((root / 'startup-error.log').is_file())

