from __future__ import annotations

from sdk.settings import CipmSettings

RUNTIME_ALIASES = frozenset({"agentarts", "agent_runtime", "runtime", "cloud"})


def is_agent_runtime(settings: CipmSettings) -> bool:
    return settings.runtime.strip().lower() in RUNTIME_ALIASES