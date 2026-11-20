"""Write the OpenAPI schema to a file without running a server (ADR 0005).

Usage: python -m app.scripts.export_openapi <output-path>
"""

import json
import sys
from pathlib import Path

from app.main import app


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("usage: python -m app.scripts.export_openapi <output-path>")
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"OpenAPI schema written to {output}")


if __name__ == "__main__":
    main()
