#!/usr/bin/env python
"""Batch processing of multiple song folders."""
import argparse
from pathlib import Path
import sys

from io_utils import get_default_io, resolve_input_path, resolve_output_path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix import process


def main():
    parser = argparse.ArgumentParser(description="Batch mix songs")
    parser.add_argument("input_root", nargs="?", help="root directory containing song folders")
    parser.add_argument("output_root", nargs="?", help="where to place mixed outputs")
    args = parser.parse_args()

    if args.input_root and args.output_root:
        inp_root = resolve_input_path(args.input_root)
        out_root = resolve_output_path(args.output_root)
    else:
        inp_root, out_root = get_default_io()

    for song_dir in Path(inp_root).iterdir():
        if song_dir.is_dir():
            out_dir = Path(out_root) / song_dir.name
            print(f"Processing {song_dir} -> {out_dir}")
            process(song_dir, out_dir)

if __name__ == "__main__":
    main()
