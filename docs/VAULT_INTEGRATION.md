# PEGASUS Vault Integration

The Valhalla Engineering Vault is an authoritative information source for PEGASUS.

## Controlled structure
- 00 CORPORATE
- 01 THE VALHALLA CODEX
- 02 INTELLECTUAL PROPERTY
- 03 ENGINEERING PROJECTS
- 04 HISTORICAL ARCHIVE

## Access model
PEGASUS can discover and account for files, paths, timestamps, sizes and SHA-256 hashes, then create administrative exceptions. The discovery interface is read-only.

PEGASUS must not silently delete, overwrite, approve, release, or alter engineering records.

## Deployment
Set VALHALLA_VAULT_PATH to the mounted/local Vault path for a deployment that can actually reach the Vault.

The GitHub worker cannot see a private/local Vault unless that Vault is deliberately exposed to the worker through an authorized storage mechanism. It does not pretend otherwise.

## Chain
Vault → PEGASUS → Sentinel Lieutenant → Minion → Result → Inspection → Archive
