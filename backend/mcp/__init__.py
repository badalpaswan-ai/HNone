"""Compatibility namespace for the legacy freight MCP entrypoint."""

from pathlib import Path
import sysconfig

_installed_mcp = Path(sysconfig.get_paths()["purelib"]) / "mcp"

if _installed_mcp.exists():
    __path__.append(str(_installed_mcp))

    _installed_init = _installed_mcp / "__init__.py"
    if _installed_init.exists():
        exec(
            compile(_installed_init.read_text(), str(_installed_init), "exec"),
            globals(),
        )
