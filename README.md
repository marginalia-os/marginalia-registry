# Marginalia Registry

Metadata-only package registry for Marginalia.

This repo stores package records, release channels, and compatibility metadata. It does not contain package source
code.

## Responsibilities

- list package versions and channels
- record checksums and signatures
- track target compatibility
- record deprecations and replacements
- feed signed catalog snapshots to the hub and firmware

## Record shape

See [`schema/catalog-entry.v1.schema.json`](./schema/catalog-entry.v1.schema.json)

## Entries

Example entries live in [`entries/`](./entries). They currently use `artifact.format: "folder-source"` and link to
package folders in `marginalia-examples`. That is a bootstrap shape for humans and the early hub. Production catalog
entries should point at immutable package archives with real checksums and signatures.

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
