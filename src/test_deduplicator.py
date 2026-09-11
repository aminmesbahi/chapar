import os
import shutil
import tempfile
import unittest

from deduplicator import deduplicate


class TestDeduplicator(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_lines(self, filename, lines):
        path = os.path.join(self.tmp_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
        return path

    def test_deduplicate_removes_matching_emails_case_insensitively(self):
        list1 = self._write_lines('list1.txt', ['a@example.com', 'B@example.com', 'c@example.com'])
        list2 = self._write_lines('list2.txt', ['b@example.com'])

        deduplicate(list1, list2)

        with open(list1, encoding='utf-8') as f:
            remaining = [line.strip() for line in f if line.strip()]

        self.assertEqual(remaining, ['a@example.com', 'c@example.com'])

    def test_deduplicate_creates_backup_file(self):
        list1 = self._write_lines('list1.txt', ['a@example.com'])
        list2 = self._write_lines('list2.txt', ['b@example.com'])

        deduplicate(list1, list2)

        backup_path = list1 + '.bak'
        self.assertTrue(os.path.exists(backup_path))
        with open(backup_path, encoding='utf-8') as f:
            backup_lines = [line.strip() for line in f if line.strip()]
        self.assertEqual(backup_lines, ['a@example.com'])

    def test_deduplicate_missing_list1_raises_system_exit(self):
        list2 = self._write_lines('list2.txt', ['b@example.com'])

        with self.assertRaises(SystemExit):
            deduplicate(os.path.join(self.tmp_dir, 'missing.txt'), list2)

    def test_deduplicate_missing_list2_raises_system_exit(self):
        list1 = self._write_lines('list1.txt', ['a@example.com'])

        with self.assertRaises(SystemExit):
            deduplicate(list1, os.path.join(self.tmp_dir, 'missing.txt'))


if __name__ == '__main__':
    unittest.main()
