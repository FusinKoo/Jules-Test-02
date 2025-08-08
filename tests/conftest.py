import sys
from pathlib import Path

# Ensure project root on path for imports
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
