import csv
import os
import shutil
import tempfile
import unittest

from merger import DEFAULT_CONFIG, get_csv_files, merge_csv


class TestMerger(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.subscribers_dir = os.path.join(self.tmp_dir, 'subscribers')
        os.makedirs(self.subscribers_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _write_csv(self, filename, rows, fieldnames):
        path = os.path.join(self.subscribers_dir, filename)
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_get_csv_files_filters_by_index_range(self):
        for name in ['000_a.csv', '001_b.csv', '002_c.csv', 'not_indexed.csv']:
            open(os.path.join(self.subscribers_dir, name), 'w').close()

        files = get_csv_files(self.subscribers_dir, 1, 2)

        self.assertEqual(files, ['001_b.csv', '002_c.csv'])

    def test_get_csv_files_no_range_returns_all_indexed_sorted(self):
        for name in ['002_c.csv', '000_a.csv', '001_b.csv']:
            open(os.path.join(self.subscribers_dir, name), 'w').close()

        files = get_csv_files(self.subscribers_dir, None, None)

        self.assertEqual(files, ['000_a.csv', '001_b.csv', '002_c.csv'])

    def test_merge_csv_keeps_latest_row_by_timestamp(self):
        fieldnames = ['Email', 'Timestamp', 'subscribe', 'subscribe_survey']
        self._write_csv('000_a.csv', [
            {'Email': 'a@b.com', 'Timestamp': '2024-01-01T00:00:00', 'subscribe': 'false', 'subscribe_survey': 'false'},
        ], fieldnames)
        self._write_csv('001_b.csv', [
            {'Email': 'A@B.com', 'Timestamp': '2024-02-01T00:00:00', 'subscribe': 'false', 'subscribe_survey': 'false'},
        ], fieldnames)

        config = DEFAULT_CONFIG.copy()
        merge_csv(self.tmp_dir, config)

        with open(os.path.join(self.tmp_dir, str(config['output_file'])), encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        # Case-insensitive email matching merges both rows into one, keeping the
        # content of whichever had the later Timestamp.
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['Timestamp'], '2024-02-01T00:00:00')

    def test_merge_csv_true_wins_regardless_of_timestamp(self):
        fieldnames = ['Email', 'Timestamp', 'subscribe', 'subscribe_survey']
        self._write_csv('000_a.csv', [
            {'Email': 'a@b.com', 'Timestamp': '2024-02-01T00:00:00', 'subscribe': 'true', 'subscribe_survey': 'false'},
        ], fieldnames)
        self._write_csv('001_b.csv', [
            {'Email': 'a@b.com', 'Timestamp': '2024-01-01T00:00:00', 'subscribe': 'false', 'subscribe_survey': 'false'},
        ], fieldnames)

        config = DEFAULT_CONFIG.copy()
        merge_csv(self.tmp_dir, config)

        with open(os.path.join(self.tmp_dir, str(config['output_file'])), encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['subscribe'], 'true')

    def test_merge_csv_no_matching_files_writes_empty_output_with_default_headers(self):
        config = DEFAULT_CONFIG.copy()
        merge_csv(self.tmp_dir, config)

        with open(os.path.join(self.tmp_dir, str(config['output_file'])), encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(rows, [])


if __name__ == '__main__':
    unittest.main()
