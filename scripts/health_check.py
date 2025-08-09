#!/usr/bin/env python
"""Command line interface to run environment health checks."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix.health import run_preflight_checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Run environment preflight checks")
    parser.add_argument("--input", help="directory with input wav files for sample rate check")
    parser.add_argument(
        "--output",
        default=".",
        help="directory used for disk space check (defaults to current directory)",
    )
    parser.add_argument("--model", help="path to required model file", default=None)
    parser.add_argument("--expected-sr", type=int, default=48000, help="expected sample rate")
    parser.add_argument(
        "--min-gpu-mem",
        type=int,
        default=1024,
        help="minimum free GPU memory in MB",
    )
    parser.add_argument(
        "--min-disk", type=int, default=1024, help="minimum free disk space in MB"
    )
    args = parser.parse_args()

    errors = run_preflight_checks(
        input_dir=args.input,
        output_dir=args.output,
        model_path=args.model,
        expected_sr=args.expected_sr,
        min_gpu_mem_mb=args.min_gpu_mem,
        min_disk_mb=args.min_disk,
    )
    if errors:
        print("Environment check failed:")
        for err in errors:
            print(f"- {err}")
        sys.exit(1)
    print("Environment check passed.")


if __name__ == "__main__":  # pragma: no cover
    main()
