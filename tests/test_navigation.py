"""Run production JavaScript under Qt's engine, without importing the shell."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

class NavigationTests(unittest.TestCase):
    def test_navigation_with_qt(self):
        runner = '/usr/lib/qt6/bin/qmltestrunner'
        if not Path(runner).exists():
            self.skipTest('QtTest unavailable; run tests/qml on an Omarchy host')
        result = subprocess.run([runner, '-input', str(Path(__file__).parent / 'qml'), '-o', '-,txt'],
            env={**__import__('os').environ, 'QT_QPA_PLATFORM':'offscreen', 'QT_QUICK_BACKEND':'software', 'QT_QPA_PLATFORMTHEME':'', 'QT_QUICK_CONTROLS_STYLE':'Basic'},
            capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
