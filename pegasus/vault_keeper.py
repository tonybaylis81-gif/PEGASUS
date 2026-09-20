from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

VAULT_SECTIONS = {
    "00 CORPORATE",
    "01 THE VALHALLA CODEX",
    "02 INTELLECTUAL PROPERTY",
    "03 ENGINEERING PROJECTS",
    "04 HISTORICAL ARCHIVE",
}

IGNORED_DIRS = {".git", "__pycache__", ".streamlit", "node_modules"}

class VaultKeeper:
    """PEGASUS Vault Keeper: inventory, classify, reconcile, and audit the Valhalla Vault."""

    def __init__(self, vault_path: str | Path, ledger_path: str | Path):
        self.vault_path = Path(vault_path).expanduser().resolve()
        self.ledger_path = Path(ledger_path).expanduser().resolve()
        self.ledger_path.mkdir(parents=True, exist_ok=True)
        self.register_path = self.ledger_path / "vault_register.json"
        self.audit_path = self.ledger_path / "vault_audit.json"
        self._ensure()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _ensure(self):
        for p in (self.register_path, self.audit_path):
            if not p.exists():
                p.write_text("[]", encoding="utf-8")

    def _read(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, path: Path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _audit(self, action: str, details: dict):
        events = self._read(self.audit_path)
        events.append({
            "timestamp": self._now(),
            "action": action,
            "actor": "VAULT KEEPER",
            "human_authorization_required": action in {
                "PROPOSE_MOVE", "PROPOSE_RENAME", "PROPOSE_ARCHIVE", "PROPOSE_DELETE"
            },
            "details": details,
        })
        self._write(self.audit_path, events)

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def inventory(self) -> list[dict]:
        if not self.vault_path.exists():
            return []
        records = []
        for path in self.vault_path.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            rel = path.relative_to(self.vault_path)
            section = rel.parts[0] if rel.parts else ""
            stat = path.stat()
            records.append({
                "path": str(rel),
                "filename": path.name,
                "extension": path.suffix.lower().lstrip("."),
                "section": section,
                "section_valid": section in VAULT_SECTIONS,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                "sha256": self._sha256(path),
            })
        records.sort(key=lambda x: x["path"].lower())
        self._write(self.register_path, records)
        self._audit("INVENTORY", {"vault": str(self.vault_path), "files": len(records)})
        return records

    def register(self) -> list[dict]:
        return self._read(self.register_path)

    def reconcile(self) -> dict:
        records = self.register()
        if not records and self.vault_path.exists():
            records = self.inventory()

        by_hash = {}
        for r in records:
            by_hash.setdefault(r["sha256"], []).append(r["path"])
        duplicates = [paths for paths in by_hash.values() if len(paths) > 1]

        invalid_sections = [
            r["path"] for r in records if not r["section_valid"]
        ]

        numbered = []
        for r in records:
            stem = Path(r["filename"]).stem.upper()
            if stem.startswith(("VEC-", "V", "DOC-", "IP-", "CORP-")):
                numbered.append(r["filename"])

        drift = []
        for name in numbered:
            if "V10" in name.upper() and "CODEX" not in name.upper():
                drift.append(name)

        report = {
            "scanned_files": len(records),
            "duplicate_groups": len(duplicates),
            "duplicates": duplicates,
            "misfiled_files": invalid_sections,
            "numbering_drift_candidates": drift,
            "unfiled_or_unknown": invalid_sections,
            "generated_at": self._now(),
        }
        self._audit("RECONCILIATION", report)
        return report

    def search(self, term: str) -> list[dict]:
        q = term.strip().lower()
        return [r for r in self.register() if q in r["path"].lower()]

    def propose_action(self, action: str, source: str, destination: str | None = None) -> dict:
        proposal = {
            "id": f"VK-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "action": action,
            "source": source,
            "destination": destination,
            "status": "AWAITING HUMAN AUTHORIZATION",
            "created_at": self._now(),
        }
        self._audit(f"PROPOSE_{action.upper()}", proposal)
        return proposal
