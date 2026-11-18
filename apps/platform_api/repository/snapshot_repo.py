from __future__ import annotations

from typing import Any

from mock.loader import dashboard_projection


class SnapshotRepo:
    def dashboard(self, farm_no: str | None = None) -> dict[str, Any]:
        return dashboard_projection(farm_no=farm_no)