"""Registry package compatibility checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


CompatibilityLevel = Literal["supported", "warning", "blocked"]


@dataclass(frozen=True)
class TargetProfile:
    device: str
    chip_family: str
    firmware_version: str
    package_api_level: int
    ram_class: str
    has_psram: bool
    supported_kinds: frozenset[str]
    supported_executions: frozenset[str]
    artifact_formats: frozenset[str]

    @classmethod
    def xteink_x4_api1(cls, firmware_version: str = "1.3.0") -> "TargetProfile":
        return cls(
            device="xteink-x4",
            chip_family="esp32-c3",
            firmware_version=firmware_version,
            package_api_level=1,
            ram_class="low",
            has_psram=False,
            supported_kinds=frozenset({"theme", "sleep_screen", "reader_module", "integration", "app"}),
            supported_executions=frozenset({"static", "module", "app"}),
            artifact_formats=frozenset({"mpkg.zip"}),
        )


@dataclass(frozen=True)
class CompatibilityReason:
    code: str
    message: str


@dataclass(frozen=True)
class CompatibilityResult:
    installable: bool
    level: CompatibilityLevel
    reasons: tuple[CompatibilityReason, ...]


RAM_CLASS_ORDER = {"low": 0, "medium": 1, "high": 2}


def parse_version(value: str) -> tuple[int, int, int] | None:
    parts = value.split(".", 2)
    if len(parts) != 3:
        return None

    parsed: list[int] = []
    for index, part in enumerate(parts):
        if index == 2:
            part = part.split("-", 1)[0].split("+", 1)[0]
        if not part.isdigit():
            return None
        parsed.append(int(part))
    return parsed[0], parsed[1], parsed[2]


def evaluate_entry(entry: dict[str, Any], profile: TargetProfile) -> CompatibilityResult:
    reasons: list[CompatibilityReason] = []

    kind = entry.get("kind")
    if isinstance(kind, str) and kind not in profile.supported_kinds:
        reasons.append(CompatibilityReason("unsupported_kind", f"Package kind '{kind}' is not supported."))

    execution = entry.get("execution")
    if isinstance(execution, str) and execution not in profile.supported_executions:
        reasons.append(CompatibilityReason("unsupported_execution", f"Execution class '{execution}' is not supported."))

    target = entry.get("target")
    if isinstance(target, dict):
        _evaluate_target(target, profile, reasons)

    artifact = entry.get("artifact")
    if isinstance(artifact, dict):
        artifact_format = artifact.get("format")
        if isinstance(artifact_format, str) and artifact_format not in profile.artifact_formats:
            reasons.append(
                CompatibilityReason("unsupported_artifact_format", f"Artifact format '{artifact_format}' is not supported.")
            )

    integrity = entry.get("integrity")
    sha256 = integrity.get("sha256") if isinstance(integrity, dict) else None
    if not isinstance(sha256, str) or not sha256:
        reasons.append(CompatibilityReason("missing_artifact_hash", "Artifact SHA-256 hash is required."))

    return CompatibilityResult(
        installable=not reasons,
        level="supported" if not reasons else "blocked",
        reasons=tuple(reasons),
    )


def _evaluate_target(target: dict[str, Any], profile: TargetProfile, reasons: list[CompatibilityReason]) -> None:
    devices = target.get("devices")
    if isinstance(devices, list) and profile.device not in devices:
        reasons.append(CompatibilityReason("unsupported_device", f"Package does not target device '{profile.device}'."))

    chip_families = target.get("chipFamilies")
    if isinstance(chip_families, list) and profile.chip_family not in chip_families:
        reasons.append(
            CompatibilityReason("unsupported_chip_family", f"Package does not target chip family '{profile.chip_family}'.")
        )

    api_level = target.get("apiLevel", 1)
    if isinstance(api_level, int) and api_level > profile.package_api_level:
        reasons.append(
            CompatibilityReason(
                "unsupported_api_level",
                f"Requires package API {api_level}; this target supports API {profile.package_api_level}.",
            )
        )

    if target.get("requiresPSRAM") is True and not profile.has_psram:
        reasons.append(CompatibilityReason("requires_psram", "Requires PSRAM, which this target does not provide."))

    ram_class = target.get("ramClass")
    if isinstance(ram_class, str) and _ram_class_too_high(ram_class, profile.ram_class):
        reasons.append(CompatibilityReason("unsupported_ram_class", f"Requires '{ram_class}' RAM class or higher."))

    min_firmware = target.get("minFirmware")
    if isinstance(min_firmware, str):
        current = parse_version(profile.firmware_version)
        required = parse_version(min_firmware)
        if current is None:
            reasons.append(
                CompatibilityReason(
                    "invalid_firmware_version", f"Firmware version '{profile.firmware_version}' is not semver-like."
                )
            )
        elif required is None:
            reasons.append(
                CompatibilityReason("invalid_min_firmware", f"Minimum firmware '{min_firmware}' is not semver-like.")
            )
        elif current < required:
            reasons.append(CompatibilityReason("requires_newer_firmware", f"Requires firmware {min_firmware} or newer."))


def _ram_class_too_high(required: str, available: str) -> bool:
    required_order = RAM_CLASS_ORDER.get(required)
    available_order = RAM_CLASS_ORDER.get(available)
    return required_order is not None and available_order is not None and required_order > available_order


def format_reasons(result: CompatibilityResult) -> list[str]:
    return [f"{reason.code}: {reason.message}" for reason in result.reasons]
