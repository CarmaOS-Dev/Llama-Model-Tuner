# core/benchmark_history.py
"""
Append-only log of every benchmark the launcher runs (Tuning Wizard and llama-bench),
so configurations and llama.cpp builds can be compared over time.
Stored as JSON Lines next to config.ini.
"""

import json
import os
from datetime import datetime

HISTORY_FILE = 'benchmark_history.jsonl'


def append_record(record, path=HISTORY_FILE):
    record = {'timestamp': datetime.now().isoformat(timespec='seconds'), **record}
    try:
        with open(path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    except OSError as e:
        print(f"[HISTORY] Could not write benchmark history: {e}")


def load_records(path=HISTORY_FILE, model=None):
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if model is None or rec.get('model') == model:
                records.append(rec)
    return records
