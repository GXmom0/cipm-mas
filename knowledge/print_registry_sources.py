from __future__ import annotations

from knowledge.registry_loader import load_real_registry


def main() -> None:
    items = load_real_registry()
    if not items:
        print("real_registry.json 为空")
        return
    for item in items:
        category = item["category"]
        print(
            f"{item['registrationNo']} | {category['aiName']}·{category['formulation']}"
            f" | {item['source']}"
        )


if __name__ == "__main__":
    main()