
"""Utility helpers shared across the pipeline."""
import datetime
import csv
import json
from pathlib import Path

def log(message: str) -> None:
    ts = datetime.datetime.now().isoformat(timespec='seconds')
    print(f"[{ts}] {message}")

def load_csv(path: str):
    log(f"Loading CSV from {path}")
    with open(path, newline='') as f:
        return list(csv.DictReader(f))

def save_json(data, path: str):
    log(f"Saving JSON to {path}")
    Path(path).parent.mkdir(exist_ok=True, parents=True)
    with open(path, 'w') as fp:
        json.dump(data, fp, indent=2)
