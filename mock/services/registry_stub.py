from __future__ import annotations

import copy
from typing import Any

from knowledge.registry_loader import load_registry


def list_items(version: str | None = None) -> list[dict[str, Any]]:
    items = [copy.deepcopy(item) for item in load_registry() if item["valid"]]
    if version is not None:
        items = [item for item in items if item["registryVersion"] == version]
    return items


def get_item(registry_item_no: str) -> dict[str, Any]:
    for item in load_registry():
        if item["registryItemNo"] == registry_item_no and item["valid"]:
            return copy.deepcopy(item)
    raise KeyError(f"登记目录项不存在：{registry_item_no}")