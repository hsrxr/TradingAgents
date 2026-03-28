import tradingagents.default_config as default_config
from typing import Dict

# Runtime dataflow config snapshot.
_config: Dict = default_config.DEFAULT_CONFIG.copy()


def set_config(config: Dict):
    """Merge runtime overrides into the active config snapshot."""
    global _config
    if config:
        _config.update(config)


def get_config() -> Dict:
    """Return a copy of the active config snapshot."""
    return _config.copy()
