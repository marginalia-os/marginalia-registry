# AGENTS.md

Guidance for agents working in `marginalia-registry`.

## Project Role

This repo is the metadata-only package registry for Marginalia. It stores package entries, channels, compatibility,
source references, artifact URLs, sizes, and hashes. It does not store package source or execute packages.

## Common Commands

Validate entries:

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

Build a catalog snapshot:

```sh
python3 tools/build_catalog.py --output dist/catalog.json
```

## Guidelines

- Entries must point to immutable release artifacts, normally `.mpkg.zip`.
- Always include artifact size and SHA-256 hash.
- Always include source URL, source ref, and source path so the community can review what produced the artifact.
- Keep schema changes synchronized with `marginalia-sdk` and `marginalia-hub`.
- Do not add package execution behavior here; registry is metadata only.
- Keep generated `dist/catalog.json` consistent with `entries/` when committed.

