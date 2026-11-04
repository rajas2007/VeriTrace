"""Module entrypoint allowing execution via: python -m veritrace."""

import sys
from veritrace.main import main

if __name__ == "__main__":
    sys.exit(main())
