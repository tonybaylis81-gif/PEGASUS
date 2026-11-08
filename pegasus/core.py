from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


SYSTEM_IDENTITY = {
    "system": "PEGASUS",
    "organization": "VALHALLA INDUSTRIAL UTILITY APPLICATIONS",
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
        # Atomic replacement prevents a partial JSON write from corrupting the ledger.
        path = self.files[kind]
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(items, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)

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
        requires_approval = assignee != "Pegasus"
        item = {
            "id": self._id("TSK"),
            "description": description.strip(),
            "assignee": assignee,
            "status": "AWAITING_APPROVAL" if requires_approval else "QUEUED",
            "human_authorization_required": requires_approval,
            "authorization_status": "PENDING" if requires_approval else "NOT_REQUIRED",
            "authorized_by": None,
            "execution_mode": "MANUAL TRACKING ONLY; no connected worker executes tasks yet",
            "result_note": "",
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        return self._append("tasks", item)

    def authorize_task(self, task_id: str, approved_by: str) -> dict:
        approved_by = approved_by.strip()
        if not approved_by:
            raise ValueError("An approving authority must be identified.")
        tasks = self._read("tasks")
        for task in tasks:
            if task["id"] != task_id:
                continue
            if not task.get("human_authorization_required"):
                raise ValueError("This task does not require human authorization.")
            if task.get("authorization_status") == "APPROVED":
                return task
            if task.get("status") in ("COMPLETE", "FAILED", "CANCELLED"):
                raise ValueError("A closed task cannot be authorized.")
            task["authorization_status"] = "APPROVED"
            task["authorized_by"] = approved_by
            task["status"] = "QUEUED"
            task["updated_at"] = self._now()
            self._write("tasks", tasks)
            self.record_event("TASK_AUTHORIZED", {
                "task_id": task_id,
                "approved_by": approved_by,
            })
            return task
        raise KeyError(f"Task not found: {task_id}")

    def update_task(self, task_id: str, status: str, result_note: str = "") -> dict:
        allowed = {"QUEUED", "IN_PROGRESS", "BLOCKED_APPROVAL", "COMPLETE", "FAILED", "CANCELLED"}
        if status not in allowed:
            raise ValueError(f"Unsupported task status: {status}")
        if status == "COMPLETE" and not result_note.strip():
            raise ValueError("A completion result or verification note is required.")
        tasks = self._read("tasks")
        for task in tasks:
            if task["id"] != task_id:
                continue
            if task.get("human_authorization_required") and task.get("authorization_status") != "APPROVED":
                if status in {"IN_PROGRESS", "COMPLETE"}:
                    raise PermissionError("Human authorization is required before this task can proceed.")
            previous = task.get("status")
            task["status"] = status
            task["result_note"] = result_note.strip() or task.get("result_note", "")
            task["updated_at"] = self._now()
            self._write("tasks", tasks)
            self.record_event("TASK_STATUS_CHANGED", {
                "task_id": task_id,
                "from": previous,
                "to": status,
                "result_note": result_note.strip(),
            })
            return task
        raise KeyError(f"Task not found: {task_id}")

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
