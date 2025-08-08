import sys
import time
from typing import Callable, Iterable, List, Optional

class BatchExecutor:
    """Execute a sequence of callables with progress and retry logic.

    Parameters
    ----------
    tasks: Iterable[Callable]
        Callables to execute. Each task is called with no arguments.
    max_retries: int, optional
        Number of times to retry a failed task. Defaults to 0 (no retries).
    bar_width: int, optional
        Width of the textual progress bar. Defaults to 20 characters.
    out: file-like object, optional
        Stream where progress is written. Defaults to ``sys.stdout``.
    """
    def __init__(self, tasks: Iterable[Callable], max_retries: int = 0,
                 bar_width: int = 20, out: Optional[object] = None) -> None:
        self.tasks: List[Callable] = list(tasks)
        self.max_retries = max_retries
        self.bar_width = bar_width
        self.out = out or sys.stdout

    # ------------------------------------------------------------------
    def _progress(self, completed: int, total: int, start: float) -> None:
        """Render progress bar with ETA."""
        elapsed = time.time() - start
        rate = elapsed / completed if completed else 0.0
        remaining = total - completed
        eta = remaining * rate
        pct = completed / total if total else 0.0
        filled = int(self.bar_width * pct)
        bar = '[' + '=' * filled + ' ' * (self.bar_width - filled) + ']'
        msg = f"\r{bar} {completed}/{total} ({pct*100:5.1f}%) ETA {eta:5.1f}s"
        self.out.write(msg)
        self.out.flush()

    # ------------------------------------------------------------------
    def run(self) -> dict:
        """Run all tasks in order.

        Returns a report dictionary containing counts and timings.
        """
        total = len(self.tasks)
        stats = {
            'total': total,
            'succeeded': 0,
            'failed': 0,
            'retries': 0,
        }
        start = time.time()
        for i, task in enumerate(self.tasks, 1):
            attempt = 0
            while True:
                try:
                    task()
                    stats['succeeded'] += 1
                    break
                except Exception:
                    if attempt < self.max_retries:
                        stats['retries'] += 1
                        attempt += 1
                        continue
                    else:
                        stats['failed'] += 1
                        break
            self._progress(i, total, start)
        self.out.write('\n')
        stats['elapsed'] = time.time() - start
        return stats

__all__ = ["BatchExecutor"]
