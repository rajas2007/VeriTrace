"""VeriTrace Native Desktop Application Entrypoint.

Initializes application bootstrap, applies High-DPI attributes,
instantiates the PySide6 QApplication, mounts the forensic workstation window,
and enters the Qt event loop.

Execution scheduled for Milestone 0.
"""

import sys
import logging
from veritrace.bootstrap import bootstrap_application
from veritrace.gui.app import VeriTraceApp

logger = logging.getLogger("veritrace.main")


def main() -> int:
    """Initialize and run the VeriTrace PySide6 desktop application."""
    bootstrap_application()
    logger.info("Starting VeriTrace Desktop...")
    app = VeriTraceApp(sys.argv)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
