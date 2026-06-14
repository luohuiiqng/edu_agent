#!/usr/bin/env python3
"""兼容入口：等价于 ``lcp chat …``。

推荐::

    cd backend && PYTHONPATH=. python -m app.cli chat "你好"
    ./scripts/lcp chat "你好"
"""

from __future__ import annotations

import os
import sys

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)


def main() -> None:
    from app.cli.main import main as cli_main

    sys.argv = [sys.argv[0], "chat"] + sys.argv[1:]
    cli_main()


if __name__ == "__main__":
    main()
