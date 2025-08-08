#!/usr/bin/env python
"""Batch processing of multiple song folders."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix import process


def main():
    parser = argparse.ArgumentParser(description="Batch mix songs")
    parser.add_argument("input_root", help="root directory containing song folders")
    parser.add_argument("output_root", help="where to place mixed outputs")
    args = parser.parse_args()
    for song_dir in Path(args.input_root).iterdir():
        if song_dir.is_dir():
            out_dir = Path(args.output_root) / song_dir.name
            if (out_dir / "report.json").exists():
                print(f"Skipping {song_dir}, already processed")
                continue
            print(f"Processing {song_dir} -> {out_dir}")
            try:
                process(song_dir, out_dir)
            except Exception as e:  # pragma: no cover
                print(f"Failed {song_dir}: {e}")

if __name__ == "__main__":
    main()
