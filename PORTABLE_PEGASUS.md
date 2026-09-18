# Portable PEGASUS

PEGASUS is designed as a portable system. The removable drive carries the system state, ledger, organizational records, Vault, archives, and bootstrap tools. The host computer supplies CPU, memory, operating system, and any optional AI model runtime.

## Portable root

```
PEGASUS/
├── CORE/
├── VAULT/
│   └── VALHALLA ENGINEERING VAULT/
├── LEDGER/
├── ARCHIVE/
├── BACKUPS/
└── PEGASUS_BOOTSTRAP/
```

The repository remains the controlled source for PEGASUS software. The portable root is the operational package.

## Moving to a new computer

1. Connect the PEGASUS removable drive.
2. Install Python and the required packages on the new computer.
3. Run `python scripts/bootstrap.py <PEGASUS-root>`.
4. Set `PEGASUS_HOME` to that root.
5. Start the Streamlit console or local administrative service.
6. Verify the ledger and Vault before normal operation.

No claim is made that a USB/SSD itself performs the computation. It transports PEGASUS and its memory/state between computers.

## Authority model

PEGASUS may perform routine administrative bookkeeping automatically.

Human authorization remains required for consequential actions, physical work, destructive testing, legal commitments, financial commitments, safety releases, or other actions outside delegated routine authority.

## Backup

Use `python scripts/backup.py <PEGASUS-root> <backup-destination>` to create a portable ZIP backup.

Keep at least one backup physically separate from the working drive.
