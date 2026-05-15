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
