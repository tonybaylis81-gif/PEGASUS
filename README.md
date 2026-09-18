# PEGASUS

**Valhalla Engineering Administrative & Command System**

PEGASUS is the proposed organizational assistant for Valhalla Engineering. Its first duty is administrative control: record keeping, document identification, filing, provenance, task accounting, and command orchestration.

## Initial chain of command

PEGASUS  
→ Sentinel Lieutenant  
→ Minion / task worker  
→ Action  
→ Result  
→ Inspection  
→ Archive

## v0.1 foundation

- Administrative record ledger
- Document registration and provenance
- Task ledger
- Command log
- Sentinel registry
- Human authorization flag
- Streamlit administrative console
- Local JSON persistence for the prototype

## Governance principle

PEGASUS can organize, record, delegate, and report. It does not silently authorize consequential physical work.

For fabrication, destructive testing, field work, or release of a prototype to human testing, the system records the required human authorization and inspection chain.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Planned expansion

1. Corporate and engineering filing taxonomy
2. Document numbering and revision control
3. Sentinel Lieutenant management
4. Minion worker queues
5. Inspection and test records
6. Human authorization gates
7. Audit trail and immutable event history
8. GitHub/Streamlit deployment workflow
9. Integration with the Valhalla Engineering Vault


## Portable architecture

PEGASUS is now structured to travel with its operational state. The removable drive can carry the portable root containing the ledger, Vault, archive, backups, manifest, and bootstrap tools. A new computer supplies the computing environment.

See `PORTABLE_PEGASUS.md` for the migration and backup procedure.
