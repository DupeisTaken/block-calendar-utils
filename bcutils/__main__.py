"""Short command entry point: python -m bcutils [options].

Both public module names use the same CLI and checkout-relative data root.
"""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
