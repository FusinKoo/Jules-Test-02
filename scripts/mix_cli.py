#!/usr/bin/env python
"""Command line interface for the mixing library."""
import argparse
import json
from pathlib import Path
import sys

from io_utils import get_default_io, resolve_input_path, resolve_output_path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import torch
except Exception:  # pragma: no cover
    torch = None

from mix import process

def main():
    parser = argparse.ArgumentParser(description="Mix stems into a single track")
    parser.add_argument("input", nargs="?", help="input directory containing stems")
    parser.add_argument("output", nargs="?", help="output directory")
    parser.add_argument("--reference", help="optional reference track")
    args = parser.parse_args()

    device = "cuda" if (torch and torch.cuda.is_available()) else "cpu"
    print(f"Using device: {device}")

    if args.input and args.output:
        inp = resolve_input_path(args.input)
        out = resolve_output_path(args.output)
    else:
        inp, out = get_default_io()

    report = process(inp, out, reference=args.reference)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
