
"""Data cleaning & feature engineering."""
from utils import log
from math_ops import square, mean

def clean_row(row):
    """Strip spaces & convert numeric fields."""
    return {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

def enrich_row(row):
    """Add squared value and flag."""
    value = float(row.get('value', 0))
    row['value_squared'] = square(value)
    row['high'] = value > 50
    return row

def process_rows(rows):
    cleaned = [enrich_row(clean_row(r)) for r in rows]
    log(f"Processed {len(rows)} rows")
    return cleaned

def compute_stats(rows):
    vals = [float(r['value']) for r in rows]
    return {'min': min(vals), 'max': max(vals), 'avg': mean(vals)}
