# Marginalia Registry

Metadata-only package registry for Marginalia.

This repo stores package records, release channels, and compatibility metadata. It does not contain package source
code. The registry follows an RT-Thread-style community index model: entries point at reviewed source repositories and
release artifacts, while users deliberately opt in to packages.

## Responsibilities

- list package versions and channels
- record source locations and release artifact checksums
- track target compatibility
- record deprecations and replacements
- feed catalog snapshots to the hub and firmware

## Record shape

See [`schema/catalog-entry.v1.schema.json`](./schema/catalog-entry.v1.schema.json)

## Entries

Example entries live in [`entries/`](./entries). Package artifacts use `artifact.format: "mpkg.zip"` and point at
release assets with fixed sizes and SHA-256 hashes. Entries also include a `source` block with the package repository,
subdirectory, and source ref used for review. Catalog signatures are intentionally optional for now; package integrity is
checked with artifact hashes and registry changes are reviewed through GitHub.

## Validate entries

```sh
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

schema = json.loads(Path("schema/catalog-entry.v1.schema.json").read_text())
validator = Draft202012Validator(schema)
for path in sorted(Path("entries").glob("*.json")):
    entry = json.loads(path.read_text())
    errors = sorted(validator.iter_errors(entry), key=lambda error: list(error.path))
    if errors:
        print(f"{path}: invalid")
        for error in errors:
            location = ".".join(str(part) for part in error.path) or "<root>"
            print(f"  {location}: {error.message}")
    else:
        print(f"{path}: ok")
PY
```

## Build a catalog snapshot

```sh
python3 tools/build_catalog.py --output dist/catalog.json
```
