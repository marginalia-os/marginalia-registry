#!/usr/bin/env python3
"""Table tests for registry compatibility checks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_compat import TargetProfile, evaluate_entry


def base_entry() -> dict[str, object]:
    return {
        "id": "org.example.package",
        "name": "Example",
        "version": "0.1.0",
        "kind": "app",
        "execution": "app",
        "channel": "experimental",
        "target": {
            "devices": ["xteink-x3", "xteink-x4"],
            "chipFamilies": ["esp32-c3"],
            "architectures": ["esp32-c3"],
            "osApi": {"major": 1, "minMinor": 0},
            "minFirmware": "1.3.0",
            "apiLevel": 1,
            "ramClass": "low",
            "requiresPSRAM": False,
        },
        "integrity": {"sha256": "abc123"},
        "artifact": {"url": "https://example.org/package.mpkg.zip", "format": "mpkg.zip", "size": 123},
    }


def v2_theme_entry() -> dict[str, object]:
    entry = base_entry()
    entry["manifestSchemaVersion"] = 2
    entry["kind"] = "theme"
    entry["execution"] = "static"
    entry["components"] = [
        {
            "id": "theme",
            "type": "contribution",
            "contract": "theme/1",
            "activation": "always",
            "requires": ["display"],
        }
    ]
    return entry


class RegistryCompatibilityTest(unittest.TestCase):
    def test_supported_entry_is_installable(self) -> None:
        result = evaluate_entry(base_entry(), TargetProfile.xteink_x4_api1())

        self.assertTrue(result.installable)
        self.assertEqual(result.level, "supported")
        self.assertEqual(result.reasons, ())

    def test_blocks_incompatible_entry(self) -> None:
        entry = base_entry()
        entry["target"] = {
            **entry["target"],  # type: ignore[arg-type]
            "devices": ["xteink-x3"],
            "minFirmware": "1.4.0",
            "apiLevel": 2,
            "requiresPSRAM": True,
        }
        entry["integrity"] = {"sha256": ""}

        result = evaluate_entry(entry, TargetProfile.xteink_x4_api1())

        self.assertFalse(result.installable)
        self.assertEqual(result.level, "blocked")
        self.assertEqual(
            [reason.code for reason in result.reasons],
            ["unsupported_device", "unsupported_api_level", "requires_psram", "requires_newer_firmware", "missing_artifact_hash"],
        )

    def test_v2_declarative_entry_keeps_the_v1_catalog_bridge(self) -> None:
        result = evaluate_entry(v2_theme_entry(), TargetProfile.xteink_x4_api1())

        self.assertTrue(result.installable)
        self.assertEqual(result.reasons, ())

    def test_v2_executable_entry_reports_native_host_boundary(self) -> None:
        entry = v2_theme_entry()
        entry["kind"] = "app"
        entry["execution"] = "app"
        entry["nativeAbi"] = "marginalia-c-1"
        entry["components"] = [
            {
                "id": "game",
                "type": "app",
                "activation": "on-demand",
            }
        ]

        result = evaluate_entry(entry, TargetProfile.xteink_x4_api1())

        self.assertFalse(result.installable)
        self.assertEqual([reason.code for reason in result.reasons], ["unsupported_native_abi"])

    def test_v2_entry_checks_architecture_and_os_api_minor(self) -> None:
        entry = v2_theme_entry()
        entry["target"] = {
            **entry["target"],  # type: ignore[arg-type]
            "architectures": ["esp32-s3"],
            "osApi": {"major": 1, "minMinor": 1},
        }

        result = evaluate_entry(entry, TargetProfile.xteink_x4_api1())

        self.assertFalse(result.installable)
        self.assertEqual([reason.code for reason in result.reasons], ["unsupported_architecture", "unsupported_os_api_minor"])


if __name__ == "__main__":
    unittest.main()
