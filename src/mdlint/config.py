"""Loads ``.mdlintrc`` config files that select which rules run.

The file is JSON with an optional ``"enabled"`` key listing rule ids. When
present, only those rules run; when absent (or the file itself doesn't
exist), every registered rule runs.
"""

import json
from pathlib import Path


class ConfigError(Exception):
    """Raised when a config file exists but can't be parsed as expected."""


def load_enabled_rule_ids(path: Path) -> list[str] | None:
    """Return the "enabled" rule id list from path, or None if unset/missing."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as err:
        raise ConfigError(f"{path}: {err}") from err

    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path}: invalid JSON: {err}") from err

    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a JSON object")

    enabled = data.get("enabled")
    if enabled is None:
        return None
    if not isinstance(enabled, list) or not all(isinstance(item, str) for item in enabled):
        raise ConfigError(f'{path}: "enabled" must be a list of rule id strings')
    return enabled
