#!/usr/bin/env python
import os
import sys
from pathlib import Path


def main() -> None:
    # src layout support
    backend_dir = Path(__file__).resolve().parent
    src_dir = backend_dir / "src"
    sys.path.insert(0, str(src_dir))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    from django.core.management import execute_from_command_line  # noqa: PLC0415

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()


