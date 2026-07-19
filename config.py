import ast
import json
import os
from typing import Any


def parse_env_mapping(key: str, default: Any = None) -> Any:
    """Parse a dotenv value that may be stored as a Python-style dict literal."""
    value = os.getenv(key)
    if value is None or value == "":
        if isinstance(default, dict):
            return default.copy()
        return default

    stripped = value.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            parsed = ast.literal_eval(stripped)
        except (SyntaxError, ValueError):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None

        if isinstance(parsed, dict):
            return parsed

    return value
