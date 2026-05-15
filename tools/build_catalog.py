#!/usr/bin/env python3
"""Build a Marginalia catalog snapshot from registry entries."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "catalog-entry.v1.schema.json"
ENTRIES_DIR = ROOT / "entries"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_entry(path: Path, validator: Draft202012Validator) -> dict[str, object]:
    entry = load_json(path)
    if not isinstance(entry, dict):
        raise ValueError(f"{path}: entry must be a JSON object")

    errors = sorted(validator.iter_errors(entry), key=lambda error: list(error.path))
    if errors:
        details = []
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            details.append(f"{location}: {error.message}")
        raise ValueError(f"{path}: " + "; ".join(details))

    return entry


def catalog_entry(entry: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in entry.items() if key != "$schema"}


def build_catalog(entries_dir: Path, generated_at: str) -> dict[str, object]:
    schema = load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    entries = [validate_entry(path, validator) for path in sorted(entries_dir.glob("*.json"))]

    return {
        "schemaVersion": 1,
        "generatedAt": generated_at,
        "signature": None,
        "entries": [catalog_entry(entry) for entry in entries],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Marginalia catalog snapshot.")
    parser.add_argument("--entries", type=Path, default=ENTRIES_DIR)
    parser.add_argument("--output", type=Path, default=Path("dist/catalog.json"))
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()

    catalog = build_catalog(args.entries, args.generated_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"entries={len(catalog['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
