
"""Simple analysis pipeline that ties everything together."""
from utils import load_csv, save_json, log
from processor import process_rows, compute_stats

def run(input_csv: str, out_dir: str = 'output') -> None:
    raw = load_csv(input_csv)
    rows = process_rows(raw)
    stats = compute_stats(rows)

    save_json(rows, f'{out_dir}/rows.json')
    save_json(stats, f'{out_dir}/summary.json')
    log(f"Pipeline complete. Stats: {stats}")

if __name__ == '__main__':
    # Generate dummy data on the fly
    import csv, random, pathlib
    input_csv = 'data.csv'
    pathlib.Path(input_csv).write_text('\n'.join(['value'] + [str(random.randint(1, 100)) for _ in range(30)]))
    run(input_csv)
