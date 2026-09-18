from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SYSTEM_IDENTITY = {
    "system": "PEGASUS",
    "organization": "VALHALLA INDUSTRIAL UTILITY APPLICATIONS INC.",
    "role": "Administrative & Command System",
    "primary_authority": "Founder, CEO, and Executive Director Jason Don Mabbutt",
    "chain": "PEGASUS -> Sentinel Lieutenant -> Minion",
    "vault": "VALHALLA ENGINEERING VAULT",
    "data_format": "Portable",
    "audit": "Enabled",
    "destructive_operations": "Disabled by default",
    "human_authorization": "Required for consequential actions",
}


class Pegasus:
    """Portable administrative core for the Valhalla PEGASUS system."""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or self._default_data_dir()).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.files = {
            "records": self.data_dir / "records.json",
            "documents": self.data_dir / "documents.json",
            "tasks": self.data_dir / "tasks.json",
            "commands": self.data_dir / "commands.json",
            "sentinels": self.data_dir / "sentinels.json",
        }
        self.manifest_path = self.data_dir / "portable_manifest.json"
        self._bootstrap()

    @staticmethod
    def _default_data_dir() -> str:
        home = os.environ.get("PEGASUS_HOME")
        if home:
            return str(Path(home) / "LEDGER")
        return str(Path("data"))

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _bootstrap(self) -> None:
        for path in self.files.values():
            if not path.exists():
                path.write_text("[]", encoding="utf-8")
        if not self._read("sentinels"):
            self._write("sentinels", [{
                "id": "SNT-0001",
                "name": "Administrative Sentinel",
                "role": "Records / Documentation / Filing",
                "status": "ACTIVE",
                "authority": "Delegated by PEGASUS",
                "created_at": self._now(),
            }])
        if not self.manifest_path.exists():
            self.manifest_path.write_text(
                json.dumps({
                    "schema_version": 1,
                    "system_identity": SYSTEM_IDENTITY,
                    "created_at": self._now(),
                    "last_initialized_at": self._now(),
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def _read(self, kind: str) -> list:
        return json.loads(self.files[kind].read_text(encoding="utf-8"))

    def _write(self, kind: str, items: list) -> None:
        self.files[kind].write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _append(self, kind: str, item: dict) -> dict:
        items = self._read(kind)
        items.append(item)
        self._write(kind, items)
        return item

    def _id(self, prefix: str) -> str:
        return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"

    def count(self, kind: str) -> int:
        return len(self._read(kind))

    def list_items(self, kind: str) -> list:
        return list(reversed(self._read(kind)))

    def log_command(self, command: str) -> dict:
        return self._append("commands", {
            "id": self._id("CMD"),
            "command": command,
            "issued_by": "HUMAN",
            "status": "LOGGED",
            "created_at": self._now(),
        })

    def create_record(self, title: str, category: str) -> dict:
        return self._append("records", {
            "id": self._id("REC"),
            "title": title,
            "category": category,
            "status": "ACTIVE",
            "created_at": self._now(),
        })

    def register_document(self, title: str, category: str, status: str) -> dict:
        return self._append("documents", {
            "id": self._id("DOC"),
            "title": title,
            "category": category,
            "status": status,
            "version": "1.0",
            "provenance": "PEGASUS",
            "created_at": self._now(),
        })

    def create_task(self, description: str, assignee: str) -> dict:
        return self._append("tasks", {
            "id": self._id("TSK"),
            "description": description,
            "assignee": assignee,
            "status": "QUEUED",
            "human_authorization_required": assignee != "Pegasus",
            "created_at": self._now(),
        })

    def record_event(self, event_type: str, details: dict) -> dict:
        return self._append("commands", {
            "id": self._id("EVT"),
            "command": event_type,
            "issued_by": "PEGASUS",
            "status": "RECORDED",
            "details": details,
            "created_at": self._now(),
        })

    def create_exception(self, description: str, assignee: str) -> dict:
        item = self.create_task(description, assignee)
        item["priority"] = "EXCEPTION"
        tasks = self._read("tasks")
        tasks[-1] = item
        self._write("tasks", tasks)
        return item
