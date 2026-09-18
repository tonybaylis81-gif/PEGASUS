from __future__ import annotations

from datetime import datetime, timezone
from .vault import VaultInterface

class AutonomousCycle:
    """Routine administrative cycle: bookkeeping, discovery and escalation only."""

    def __init__(self, pegasus, vault_path: str):
        self.pegasus = pegasus
        self.vault = VaultInterface(vault_path)

    def run(self) -> dict:
        today = datetime.now(timezone.utc).date().isoformat()
        title = f"PEGASUS Daily Administrative Cycle {today}"
        if not any(r.get("title") == title for r in self.pegasus._read("records")):
            self.pegasus.create_record(title, "Administrative")

        status = self.vault.status()
        self.pegasus.record_event("VAULT_SCAN", status)

        if not status["accessible"]:
            self.pegasus.create_exception(
                "Valhalla Engineering Vault is not accessible to PEGASUS.",
                "HUMAN",
            )
        return status
