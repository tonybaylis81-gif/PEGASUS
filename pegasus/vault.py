from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

VAULT_ROOTS = (
    "00 CORPORATE",
    "01 THE VALHALLA CODEX",
    "02 INTELLECTUAL PROPERTY",
    "03 ENGINEERING PROJECTS",
    "04 HISTORICAL ARCHIVE",
)

class VaultInterface:
    """Read-only discovery and accounting interface for the Valhalla Engineering Vault."""

    def __init__(self, vault_path: str):
        self.root = Path(vault_path).expanduser().resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def exists(self) -> bool:
        return self.root.is_dir()

    def scan(self) -> list[dict]:
        if not self.exists():
            return []
        items = []
        for root_name in VAULT_ROOTS:
            section = self.root / root_name
            if not section.is_dir():
                continue
            for path in sorted(p for p in section.rglob("*") if p.is_file()):
                stat = path.stat()
                items.append({
                    "path": str(path.relative_to(self.root)),
                    "name": path.name,
                    "extension": path.suffix.lower(),
                    "section": root_name,
                    "size_bytes": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "sha256": self._hash(path),
                    "accounted_at": self._now(),
                })
        return items

    def status(self) -> dict:
        inventory = self.scan()
        sections = {section: 0 for section in VAULT_ROOTS}
        for item in inventory:
            sections[item["section"]] += 1
        return {
            "vault_path": str(self.root),
            "accessible": self.exists(),
            "files_accounted": len(inventory),
            "sections": sections,
        }
