"""Architecture boundary tests for VeriTrace.

Ensures that AST import rules are verified within pytest test suites.
"""

import sys
from pathlib import Path

# Add scripts directory to path to import validator
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts" / "validation"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_architecture


def test_architecture_boundaries_pass():
    """Verify that all layer import boundaries in src/veritrace are respected."""
    exit_code = check_architecture.main()
    assert exit_code == 0, "Architecture boundary validation failed with violations."
