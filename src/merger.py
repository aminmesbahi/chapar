import os
import csv
import configparser
import argparse
from datetime import datetime

DEFAULT_CONFIG = {
    'csv_file': 'subscribers',
    'output_file': 'subscribers.csv',
    'email_column': 'Email',
    'updates_column': 'subscrube',
    'survey_column': 'subscribe_survey',
    'start_index': None,
    'end_index': None
}

def load_merger_config(folder):
    config_path = os.path.join(folder, 'merger.ini')
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(config_path):
        parser = configparser.ConfigParser()
        parser.read(config_path, encoding='utf-8')
        if parser.has_section('Columns'):
            for key in DEFAULT_CONFIG.keys():
                if parser.has_option('Columns', key):
                    config[key] = parser.get('Columns', key)
    return config

def get_csv_files(subscribers_folder, start_idx, end_idx):
    files = []
    for fname in os.listdir(subscribers_folder):
        if fname.endswith('.csv') and fname[0:3].isdigit():
            idx = int(fname[0:3])
            if (start_idx is None or idx >= start_idx) and (end_idx is None or idx <= end_idx):
                files.append((idx, fname))
    files.sort()
    return [fname for idx, fname in files]

def merge_csv(folder, config):
    # Always look for CSVs in the 'subscribers' subfolder
    subscribers_folder = os.path.join(folder, 'subscribers')
    start_idx = int(config['start_index']) if config['start_index'] else None
    end_idx = int(config['end_index']) if config['end_index'] else None
    output_path = os.path.join(folder, config['output_file'])

    files = get_csv_files(subscribers_folder, start_idx, end_idx)
    merged = {}

    for fname in files:
        path = os.path.join(subscribers_folder, fname)
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get(config['email_column'], '').strip().lower()
                if not email:
                    continue
                timestamp = row.get('Timestamp', '')
                try:
                    ts = datetime.fromisoformat(timestamp)
                except Exception:
                    ts = datetime.min
                if email not in merged or ts > merged[email]['_ts']:
                    merged[email] = {
                        **row,
                        '_ts': ts
                    }
                else:
                    # For each field, True always wins over False, regardless of timestamp
                    for col in [config['updates_column'], config['survey_column']]:
                        prev_val = merged[email].get(col, '').strip().lower()
                        curr_val = row.get(col, '').strip().lower()
                        if curr_val == 'true' or prev_val == '':
                            merged[email][col] = row.get(col, '')
                        elif curr_val == 'false' and prev_val != 'true':
                            merged[email][col] = row.get(col, '')

    # Remove _ts before writing
    if merged:
        fieldnames = [k for k in next(iter(merged.values())).keys() if k != '_ts']
    else:
        fieldnames = [config['email_column'], config['updates_column'], config['survey_column']]
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in merged.values():
            out_row = {k: v for k, v in row.items() if k != '_ts'}
            writer.writerow(out_row)

    print(f"Merged {len(merged)} unique subscribers to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Merge and deduplicate subscribers CSV")
    parser.add_argument('folder', nargs='?', default='.', help='Folder containing merger.ini and the subscribers subfolder')
    parser.add_argument('--start', type=int, help='Start index (e.g. 2 for 002)')
    parser.add_argument('--end', type=int, help='End index (e.g. 4 for 004)')
    args = parser.parse_args()

    config = load_merger_config(args.folder)
    if args.start is not None:
        config['start_index'] = str(args.start).zfill(3)
    if args.end is not None:
        config['end_index'] = str(args.end).zfill(3)
    merge_csv(args.folder, config)

if __name__ == '__main__':
    main()