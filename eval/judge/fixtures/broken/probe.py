"""DELIBERATELY BROKEN CONTROL FIXTURE - do not treat this as a real game.

The probe recipe exists so the directory has the right shape, but the protocol
is not implemented: this prints a message to stderr and exits 1, whether it is
asked for the interactive form or the --file form. Nothing is ever written to
stdout.
"""

from __future__ import annotations

import sys


def main(argv: list) -> int:
    print("probe: not implemented in this submission", file=sys.stderr)
    if argv:
        print("probe: ignoring arguments %r" % (argv,), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
