import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('tidyup', Path(__file__).resolve().parents[1] / 'backend/tidyup.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.tidy = m.TidyUp(self.home)
        self.tidy.packages = lambda: {'chromium', 'omarchy'}
        self.tidy.catalogue = lambda: {'apps': [{'id': 'chromium', 'desktopIds': ['chromium']}]}
        for root in self.tidy.roots.values():
            root.mkdir(parents=True, exist_ok=True)
        self.folder = self.tidy.roots['Cache'] / 'chromium'
        self.folder.mkdir()
        (self.folder / 'sample').write_text('test data')

    def selection(self):
        return [{'id': i['id'], 'fingerprint': i['fingerprint']} for i in self.tidy.scan('chromium')['items']]

    def move(self):
        result = self.tidy.clean('chromium', self.selection())
        self.assertFalse(result['failures'])
        return result['moved'][0]

    def test_fingerprint_survives_javascript_json_roundtrip(self):
        selection = self.selection()
        self.assertTrue(all(isinstance(part, str) for part in selection[0]['fingerprint']))
        self.assertGreater(int(selection[0]['fingerprint'][2]), 2**53)
        self.assertEqual(len(self.tidy.clean('chromium', __import__('json').loads(__import__('json').dumps(selection)))['moved']), 1)

    def test_uninstall_uses_system_pacman_with_confirmation(self):
        process = __import__('unittest.mock', fromlist=['Mock']).Mock()
        process.wait.return_value = 0
        with patch.object(m.subprocess, 'Popen', return_value=process) as launch:
            self.tidy.uninstall('chromium')
            argv = launch.call_args.args[0]
            self.assertEqual(argv, ['/usr/bin/omarchy-launch-terminal', '/usr/bin/sudo', '/usr/bin/pacman', '-R', '--', 'chromium'])
            self.assertNotIn('--noconfirm', argv)
        with self.assertRaises(ValueError):
            self.tidy.uninstall('--help')

    def test_scan_is_read_only_and_exact(self):
        (self.folder.parent / 'chromium-unrelated').mkdir()
        result = self.tidy.scan('chromium')
        self.assertEqual([i['id'] for i in result['items']], ['Cache:chromium'])
        self.assertEqual(result['items'][0]['bytes'], 9)
        self.assertFalse(self.tidy.recovery.exists())

    def test_move_and_restore_preserve_content(self):
        token = self.move()
        self.assertFalse(self.folder.exists())
        self.assertEqual(len(self.tidy.history()['entries']), 1)
        self.tidy.restore(token)
        self.assertEqual((self.folder / 'sample').read_text(), 'test data')
        self.assertEqual(self.tidy.history()['entries'], [])

    def test_restore_never_overwrites_new_data(self):
        token = self.move()
        self.folder.mkdir()
        (self.folder / 'new').write_text('new data')
        with self.assertRaisesRegex(ValueError, 'not been overwritten'):
            self.tidy.restore(token)
        self.assertEqual((self.folder / 'new').read_text(), 'new data')
        self.assertEqual(len(self.tidy.history()['entries']), 1)

    def test_stale_selection_rejected_before_moves(self):
        selection = self.selection()
        (self.folder / 'new').write_text('new')
        with self.assertRaisesRegex(ValueError, 'changed since review'):
            self.tidy.clean('chromium', selection)
        self.assertTrue(self.folder.exists())

    def test_unknown_and_duplicate_selections_rejected(self):
        selection = self.selection()
        with self.assertRaises(ValueError):
            self.tidy.clean('chromium', selection * 2)
        with self.assertRaises(ValueError):
            self.tidy.clean('chromium', [{'id': 'Data:../documents', 'fingerprint': []}])
        self.assertTrue(self.folder.exists())

    def test_symlink_root_not_followed(self):
        target = self.home / 'outside'
        self.folder.parent.rename(target)
        self.folder.parent.symlink_to(target, target_is_directory=True)
        result = self.tidy.scan('chromium')
        self.assertFalse(result['items'])
        self.assertTrue(result['warnings'])

    def test_symlink_candidate_not_selected(self):
        target = self.home / 'outside'
        self.folder.rename(target)
        self.folder.symlink_to(target, target_is_directory=True)
        self.assertFalse(self.tidy.scan('chromium')['items'])

    def test_nested_symlinks_preserved_without_following(self):
        external = self.home / 'external'
        external.write_text('keep')
        (self.folder / 'link').symlink_to(external)
        token = self.move()
        self.tidy.restore(token)
        self.assertTrue((self.folder / 'link').is_symlink())
        self.assertEqual(external.read_text(), 'keep')

    def test_restore_blocks_symlink_parent(self):
        token = self.move()
        original = self.folder.parent
        target = self.home / 'redirected'
        original.rename(target)
        original.symlink_to(target)
        with self.assertRaises(OSError):
            self.tidy.restore(token)
        self.assertFalse((target / 'chromium').exists())

    def test_recovery_symlink_denied(self):
        self.tidy.recovery.parent.mkdir(parents=True)
        self.tidy.recovery.symlink_to(self.home)
        with self.assertRaises(OSError):
            self.move()
        self.assertTrue(self.folder.exists())

    def test_protected_folder_not_offered(self):
        (self.tidy.roots['Settings'] / 'omarchy').mkdir()
        self.assertFalse(self.tidy.scan('omarchy')['items'])

    def test_leftovers_respect_alternative_package(self):
        folder = self.tidy.roots['Settings'] / 'Code'
        folder.mkdir()
        self.tidy.packages = lambda: {'visual-studio-code-bin'}
        self.assertNotIn('Settings:Code', [i['id'] for i in self.tidy.scan('leftovers')['items']])
        self.tidy.packages = lambda: set()
        self.assertIn('Settings:Code', [i['id'] for i in self.tidy.scan('leftovers')['items']])

    def test_missing_package_not_treated_as_installed(self):
        with self.assertRaises(ValueError):
            self.tidy.scan('not-installed')

    def test_interrupted_move_has_receipt_but_no_false_history(self):
        with patch.object(m, 'rename_exclusive', side_effect=OSError('simulated failure')):
            result = self.tidy.clean('chromium', self.selection())
        self.assertEqual(len(result['failures']), 1)
        self.assertTrue(self.folder.exists())
        self.assertEqual(self.tidy.history()['entries'], [])

    def test_partial_batch_keeps_success_recoverable(self):
        (self.tidy.roots['Settings'] / 'chromium').mkdir()
        original = m.rename_exclusive
        calls = []
        def sometimes(*args):
            calls.append(args)
            if len(calls) == 2:
                raise OSError('simulated second failure')
            return original(*args)
        with patch.object(m, 'rename_exclusive', side_effect=sometimes):
            result = self.tidy.clean('chromium', self.selection())
        self.assertEqual(len(result['moved']), 1)
        self.assertEqual(len(result['failures']), 1)
        self.assertEqual(len(self.tidy.history()['entries']), 1)

    def test_purge_only_removes_recovery_object(self):
        external = self.home / 'keep'
        external.write_text('keep')
        (self.folder / 'link').symlink_to(external)
        token = self.move()
        self.tidy.purge(token)
        self.assertEqual(external.read_text(), 'keep')
        self.assertEqual(self.tidy.history()['entries'], [])
        with self.assertRaises(ValueError):
            self.tidy.purge('../keep')

    def test_purge_rejects_substituted_symlink(self):
        token = self.move()
        data = self.tidy.recovery / (token + '.data')
        data.rename(self.tidy.recovery / 'saved')
        data.symlink_to(self.home)
        with self.assertRaises(ValueError):
            self.tidy.purge(token)
        self.assertTrue(self.home.exists())

    def test_mounted_content_not_offered_or_deleted(self):
        with patch.object(m, 'mountpoints', return_value=[self.folder / 'mounted']):
            self.assertFalse(self.tidy.scan('chromium')['items'])
        token = self.move()
        with patch.object(m, 'mountpoints', return_value=[self.tidy.recovery / (token + '.data') / 'mounted']):
            with self.assertRaisesRegex(ValueError, 'mounted content'):
                self.tidy.purge(token)
        self.assertEqual(len(self.tidy.history()['entries']), 1)

    def test_traversal_token_rejected(self):
        with self.assertRaises(ValueError):
            self.tidy.restore('../receipt')

    def test_recovery_permissions_checked(self):
        self.tidy.recovery.mkdir(parents=True, mode=0o755)
        with self.assertRaises(ValueError):
            self.move()

    def test_command_output_and_deadline_bounded(self):
        with self.assertRaisesRegex(ValueError, 'output exceeded'):
            m.command(['/usr/bin/python3', '-I', '-c', 'print("x" * 100000)'], limit=1000)
        with self.assertRaisesRegex(ValueError, 'timed out'):
            m.command(['/usr/bin/python3', '-I', '-c', 'import time; time.sleep(2)'], timeout=.1)

    def test_command_stderr_bounded(self):
        with self.assertRaisesRegex(ValueError, 'output exceeded'):
            m.command(['/usr/bin/python3', '-I', '-c', 'import sys; sys.stderr.write("x" * 100000)'], limit=1000)

if __name__ == '__main__':
    unittest.main()
