#!/usr/bin/env python
"""Command line tool for selecting RVC models."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mix.model_manager import get_model_path


def main():
    parser = argparse.ArgumentParser(description="Select RVC model")
    parser.add_argument("--model", help="path to model file (.pth)")
    parser.add_argument("--ui", action="store_true",
                        help="interactive selection when needed")
    args = parser.parse_args()
    path = get_model_path(cli_path=args.model, use_ui=args.ui)
    print(path)


if __name__ == "__main__":
    main()
