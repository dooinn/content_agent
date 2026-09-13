"""Run the API with `uv run python -m app`.

psycopg's async driver cannot run on Windows' default Proactor event loop, and uvicorn picks
that loop when reload is off, so we choose the loop ourselves.
"""

import asyncio
import os
import sys

import uvicorn


def main() -> None:
    config = uvicorn.Config(
        "app.main:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000"))
    )
    loop_factory = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    asyncio.run(uvicorn.Server(config).serve(), loop_factory=loop_factory)


if __name__ == "__main__":
    main()
