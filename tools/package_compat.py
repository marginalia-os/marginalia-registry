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
    supported_architectures: frozenset[str] = frozenset()
    supported_os_api_major: int = 1
    supported_os_api_minor: int = 0
    supported_native_abis: frozenset[str] = frozenset()
    # New profiles can advertise native hosts per executable component role.
    # Keep supported_native_abis as the compatibility fallback for older
    # callers that only know the package-wide capability.
    supported_native_abis_by_role: tuple[tuple[str, frozenset[str]], ...] = ()

    def native_abis_for_role(self, role: str) -> frozenset[str]:
        if not self.supported_native_abis_by_role:
            return self.supported_native_abis
        return dict(self.supported_native_abis_by_role).get(role, frozenset())

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
            supported_architectures=frozenset({"esp32-c3"}),
            supported_os_api_major=1,
            supported_os_api_minor=0,
            supported_native_abis=frozenset(),
            supported_native_abis_by_role=(("service", frozenset({"marginalia-c-1"})),),
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
NATIVE_MODULE_ENTRYPOINT = "marginalia_module_entry_v1"
ALLOWED_ACTIVATIONS = {
    "app": frozenset({"on-demand"}),
    "service": frozenset({"manual", "boot", "always"}),
    "provider": frozenset({"on-demand"}),
    "contribution": frozenset({"always"}),
}


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

    manifest_schema_version = entry.get("manifestSchemaVersion", 1)
    if isinstance(manifest_schema_version, int) and manifest_schema_version > 2:
        reasons.append(
            CompatibilityReason(
                "unsupported_schema", f"Manifest schema version {manifest_schema_version} is not supported."
            )
        )

    kind = entry.get("kind")
    if isinstance(kind, str) and kind not in profile.supported_kinds:
        reasons.append(CompatibilityReason("unsupported_kind", f"Package kind '{kind}' is not supported."))

    execution = entry.get("execution")
    if isinstance(execution, str) and execution not in profile.supported_executions:
        reasons.append(CompatibilityReason("unsupported_execution", f"Execution class '{execution}' is not supported."))

    if manifest_schema_version == 2:
        components = entry.get("components")
        for component in components or []:
            if not isinstance(component, dict):
                continue
            role = component.get("type")
            activation = component.get("activation")
            if role in ALLOWED_ACTIVATIONS and activation not in ALLOWED_ACTIVATIONS[role]:
                reasons.append(
                    CompatibilityReason(
                        "invalid_activation_for_role",
                        f"Activation '{activation or '<missing>'}' is not valid for {role} components.",
                    )
                )
        executable_components = [
            component
            for component in components or []
            if isinstance(component, dict) and component.get("type") in {"app", "service", "provider"}
        ]
        executable = bool(executable_components)
        if executable and isinstance(components, list) and any(
            not isinstance(component, dict)
            or component.get("type") in {"app", "service", "provider"}
            and component.get("entrypoint") != NATIVE_MODULE_ENTRYPOINT
            for component in components
        ):
            reasons.append(
                CompatibilityReason(
                    "invalid_native_entrypoint",
                    f"Executable components must use '{NATIVE_MODULE_ENTRYPOINT}'.",
                )
            )
        native_abi = entry.get("nativeAbi")
        for component in executable_components:
            role = component.get("type")
            if not isinstance(native_abi, str) or native_abi not in profile.native_abis_for_role(role):
                reasons.append(
                    CompatibilityReason(
                        "unsupported_native_abi",
                        f"Native ABI '{native_abi or '<missing>'}' is not supported for {role} components.",
                    )
                )

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

    architectures = target.get("architectures")
    if isinstance(architectures, list) and not any(
        isinstance(architecture, str) and architecture in profile.supported_architectures
        for architecture in architectures
    ):
        reasons.append(
            CompatibilityReason(
                "unsupported_architecture", f"Package does not target architecture for '{profile.device}'."
            )
        )

    os_api = target.get("osApi")
    if isinstance(os_api, dict):
        major = os_api.get("major")
        min_minor = os_api.get("minMinor", 0)
        if isinstance(major, int) and major != profile.supported_os_api_major:
            reasons.append(
                CompatibilityReason(
                    "unsupported_os_api",
                    f"Requires OS API major {major}; this target provides major {profile.supported_os_api_major}."
                )
            )
        elif isinstance(min_minor, int) and min_minor > profile.supported_os_api_minor:
            reasons.append(
                CompatibilityReason(
                    "unsupported_os_api_minor",
                    f"Requires OS API minor {min_minor}; this target provides minor {profile.supported_os_api_minor}."
                )
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
