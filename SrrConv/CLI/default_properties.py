"""
This file was created for the SRRConverter project
License: GPLv3

Description: Manages persistent default properties (config.yaml)
Author: Zatarita
"""

import pickle
import yaml
from pathlib import Path

_CONFIG_PATH = Path("config.yaml")
_LEGACY_PATH = Path("config.defaults")

DEFAULT_PROPERTIES = {
    "hash_manifest": "./file_hashes.manifest",
    "log_file": "./output.log",
    "out_path": "./",
    "image_format": "dds",
    "sr_directory": "C:/Program Files (x86)/Steam/steamapps/common/Soul Reaver I-II/",
    "def_directory": "C:/Program Files (x86)/Steam/steamapps/common/Legacy of Kain Defiance Remastered/",
    "log_level": "info"
}

_properties: dict | None = None


def _load_properties() -> dict:
    """Load properties from YAML, migrating from pickle if needed."""
    global _properties
    if _properties is not None:
        return _properties

    if _LEGACY_PATH.exists():
        with open(_LEGACY_PATH, "rb") as f:
            legacy = pickle.load(f)
        _properties = {k: str(v) if isinstance(v, Path) else v for k, v in legacy.items()}
        _save_yaml(_properties)
        try:
            _LEGACY_PATH.unlink()
        except OSError:
            pass

    elif _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            loaded = yaml.safe_load(f)
        _properties = loaded if isinstance(loaded, dict) else dict(DEFAULT_PROPERTIES)

    else:
        _properties = dict(DEFAULT_PROPERTIES)
        _save_yaml(_properties)

    return _properties


def _save_yaml(properties: dict) -> None:
    """Write properties dict to YAML config file."""
    with open(_CONFIG_PATH, "w") as f:
        yaml.dump(properties, f, default_flow_style=False)


def get_default_property(key: str, logger) -> str | Path | None:
    """Return a default property value; path-like values are returned as Path objects."""
    properties = _load_properties()
    if key not in properties:
        if logger:
            logger.error(f"No property `{key}` found in defaults")
        return None
    value = properties[key]
    if isinstance(value, str) and ("/" in value or "\\" in value):
        return Path(value)
    return value


def list_defaults() -> dict:
    """Return all default properties."""
    return dict(_load_properties())


def set_default_property(key: str, value, logger) -> None:
    """Set a default property and persist to YAML."""
    properties = _load_properties()
    properties[key] = value
    _save_yaml(properties)


def generate_new_defaults():
    """When no config exists, create them from DEFAULT_PROPERTIES."""
    _save_yaml(dict(DEFAULT_PROPERTIES))