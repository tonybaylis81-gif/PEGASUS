# PEGASUS Vault Integration

The existing Valhalla Engineering Vault is the authoritative engineering record. PEGASUS must connect to that Vault, not silently create an empty replacement and call it connected.

## Controlled structure

- 00 CORPORATE
- 01 THE VALHALLA CODEX
- 02 INTELLECTUAL PROPERTY
- 03 ENGINEERING PROJECTS
- 04 HISTORICAL ARCHIVE

## Access model

PEGASUS may discover, index, hash, search and report on Vault files. The current Vault Keeper is read-only. It must not silently delete, overwrite, rename, move, approve, release or alter engineering records.

## Streamlit Community Cloud

Set `VALHALLA_VAULT_PATH` to the actual Vault directory only when that directory is mounted and accessible to the running app. The app now checks that the directory exists before displaying a connected status. It does not create the Vault directory during startup.

A ZIP import is an explicit copy operation. It preserves the uploaded source and avoids overwriting differing files, but a copy placed on Streamlit Community Cloud's local filesystem is not a durable storage strategy. Community Cloud local files may be lost on restart, rebuild or redeploy.

The production connection therefore requires a durable cloud storage location that the app can authenticate to, plus persistent storage for the Pegasus ledgers. Do not put Vault contents or credentials in the public GitHub repository.

## Current chain

Vault → PEGASUS → Sentinel Lieutenant → Minion → Result → Inspection → Archive

Planning and task records are not proof that a worker has executed a task. Actual delegation, execution, result verification and human authorization remain separate capabilities to be implemented and tested.
