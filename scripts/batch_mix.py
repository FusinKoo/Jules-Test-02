#!/usr/bin/env python
"""Batch processing of multiple song folders with progress and retries."""
import argparse
from functools import partial
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix import process
from batch import BatchExecutor
from mix.deterministic import enable_determinism


def main():
    parser = argparse.ArgumentParser(
        description="Batch mix songs (exports 48 kHz/24-bit WAV)"
    )
    parser.add_argument("input_root", help="root directory containing song folders")
    parser.add_argument("output_root", help="where to place mixed outputs")
    parser.add_argument("--retries", type=int, default=0,
                        help="number of times to retry failed mixes")
    parser.add_argument(
        "--seed",
        type=int,
        help="set random seed and enable deterministic backends",
    )
    args = parser.parse_args()
    if args.seed is not None:
        enable_determinism(args.seed)
    tasks = []
    for song_dir in Path(args.input_root).iterdir():
        if song_dir.is_dir():
            out_dir = Path(args.output_root) / song_dir.name
            tasks.append(partial(process, song_dir, out_dir))
    if not tasks:
        print("No song folders found.")
        return
    executor = BatchExecutor(tasks, max_retries=args.retries)
    report = executor.run()
    print(f"Completed: {report['succeeded']} succeeded, {report['failed']} failed, "
          f"retries: {report['retries']}, elapsed: {report['elapsed']:.1f}s")


if __name__ == "__main__":
    main()
