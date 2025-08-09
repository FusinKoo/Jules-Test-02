#!/usr/bin/env python
"""Local file-based processing pipeline."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix import process
from pipeline_common import build_parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.dry_run:
        print("Dry run: no processing performed")
        return
    model_paths = [Path(args.rvc_model)] if args.rvc_model else None
    report = process(Path(args.input), Path(args.output), model_paths=model_paths)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
