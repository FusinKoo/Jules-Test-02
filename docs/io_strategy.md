# I/O Path Strategy

This project supports two storage channels: the local `/content` filesystem and Google Drive. The utilities in `scripts/io_utils.py` provide unified path handling to avoid permission and path issues.

## Default Directories

- **Local**: `/content/input` and `/content/output`
- **Drive**: `/content/drive/MyDrive/input` and `/content/drive/MyDrive/output`

`get_default_io()` attempts to mount Google Drive and falls back to the local filesystem if the mount fails.

## Mounting with Fallback

The code tries to `google.colab.drive.mount("/content/drive")`. If the attempt raises an exception or the path does not exist, local paths are used.

## Space & Permission Checks

`resolve_output_path()` ensures the target directory exists, is readable and writable, and has at least 100 MB free space. This helps stability with large files.

## Usage Examples

```python
from scripts.io_utils import get_default_io, resolve_input_path

# Use defaults (Drive when available, otherwise local)
inp, out = get_default_io()

# Explicit paths, converted to absolute paths with checks
inp = resolve_input_path("~/data/song1")
out = resolve_output_path("~/results/song1")
```

When running inside Colab:

```bash
!python scripts/mix_cli.py               # uses defaults
!python scripts/mix_cli.py /path/in /path/out
```

On a workstation the same code works with the local filesystem only.
