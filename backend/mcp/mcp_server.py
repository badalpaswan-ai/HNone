"""Compatibility entrypoint. Prefer: cd backend && python -m app.mcp_server"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
