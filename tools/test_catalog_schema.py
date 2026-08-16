#!/usr/bin/env python3
"""Schema tests for executable v2 catalog metadata."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


def executable_entry(entrypoint: str) -> dict[str, object]:
    return {
        "$schema": "../schema/catalog-entry.v1.schema.json",
        "id": "org.example.native-app",
        "name": "Native App",
        "version": "1.0.0",
        "manifestSchemaVersion": 2,
        "kind": "app",
        "execution": "app",
        "channel": "experimental",
        "components": [
            {
                "id": "app",
                "type": "app",
                "activation": "on-demand",
                "entrypoint": entrypoint,
            }
        ],
        "nativeAbi": "marginalia-c-1",
        "source": {"type": "git", "url": "https://example.org/source.git", "ref": "v1.0.0"},
        "target": {
            "devices": ["xteink-x4"],
            "chipFamilies": ["esp32-c3"],
            "architectures": ["esp32-c3"],
            "minFirmware": "1.3.0",
            "apiLevel": 1,
            "ramClass": "low",
            "requiresPSRAM": False,
        },
        "integrity": {"sha256": "a" * 64},
        "artifact": {"url": "https://example.org/native-app.mpkg.zip", "format": "mpkg.zip", "size": 123},
    }


class CatalogSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        schema = json.loads((ROOT / "schema" / "catalog-entry.v1.schema.json").read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema)

    def test_executable_v2_catalog_requires_fixed_entrypoint(self) -> None:
        errors = list(self.validator.iter_errors(executable_entry("marginalia_module_entry_v1")))
        self.assertEqual(errors, [])

        errors = list(self.validator.iter_errors(executable_entry("launch")))
        self.assertTrue(any("marginalia_module_entry_v1" in error.message for error in errors))


if __name__ == "__main__":
    unittest.main()
