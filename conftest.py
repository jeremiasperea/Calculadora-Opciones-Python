# Root conftest for pytest
# Ensures the repo root is added to sys.path for imports
import sys
from pathlib import Path

repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
