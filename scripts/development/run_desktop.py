"""Developer Launch Script for VeriTrace Desktop."""

import sys
from pathlib import Path

# Add src to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
src_dir = root_dir / "src"
sys.path.insert(0, str(src_dir))

if __name__ == "__main__":
    from veritrace.main import main
    sys.exit(main())
