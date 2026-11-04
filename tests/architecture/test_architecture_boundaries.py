"""Architecture boundary tests for VeriTrace.

Ensures that AST import rules are verified within pytest test suites.
"""

import check_architecture


def test_architecture_boundaries_pass():
    """Verify that all layer import boundaries in src/veritrace are respected."""
    exit_code = check_architecture.main()
    assert exit_code == 0, "Architecture boundary validation failed with violations."
