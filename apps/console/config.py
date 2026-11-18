from __future__ import annotations

from sdk.settings import CipmSettings


def load_settings() -> CipmSettings:
    return CipmSettings.from_env()