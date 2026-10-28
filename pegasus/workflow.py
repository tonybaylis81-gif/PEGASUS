from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


STATUSES = ("PLANNED", "IN_PROGRESS", "BLOCKED_APPROVAL", "COMPLETE", "FAILED")


class WorkflowLedger:
    """Persistent goal and step tracker. Planning is not execution or authorization."""

    def __init__(self, ledger_dir: str | Path):
        self.ledger_dir = Path(ledger_dir).expanduser().resolve()
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.ledger_dir / "workflows.json"
        self.audit_path = self.ledger_dir / "workflow_audit.json"
        if not self.path.exists():
            self._write(self.path, [])
        if not self.audit_path.exists():
            self._write(self.audit_path, [])

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _write(path: Path, data: list[dict]) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)

    @staticmethod
    def _read(path: Path) -> list[dict]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Ledger must contain a JSON list: {path.name}")
        return data

    def list_workflows(self) -> list[dict]:
        return list(reversed(self._read(self.path)))

    def _audit(self, action: str, details: dict) -> None:
        events = self._read(self.audit_path)
        events.append({
            "id": f"AUD-{uuid4().hex[:10].upper()}",
            "timestamp": self._now(),
            "actor": "HUMAN-INITIATED PEGASUS WORKFLOW",
            "action": action,
            "details": details,
        })
        self._write(self.audit_path, events)

    def create(self, goal: str, steps: list[str], owner: str = "Pegasus") -> dict:
        goal = goal.strip()
        cleaned_steps = [step.strip() for step in steps if step.strip()]
        if not goal:
            raise ValueError("A goal is required.")
        if not cleaned_steps:
            raise ValueError("At least one step is required.")
        if len(cleaned_steps) > 100:
            raise ValueError("A workflow may contain no more than 100 steps.")
        now = self._now()
        item = {
            "id": f"WF-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}",
            "goal": goal,
            "owner": owner,
            "status": "PLANNED",
            "human_authorization_required_for_consequential_actions": True,
            "execution_note": "Plan recorded only. No external actions were executed.",
            "created_at": now,
            "updated_at": now,
            "steps": [
                {
                    "id": f"STEP-{i:03d}",
                    "description": description,
                    "status": "PLANNED",
                    "human_authorization_required": True,
                    "updated_at": now,
                }
                for i, description in enumerate(cleaned_steps, start=1)
            ],
        }
        items = self._read(self.path)
        items.append(item)
        self._write(self.path, items)
        self._audit("WORKFLOW_CREATED", {"workflow_id": item["id"], "goal": goal, "step_count": len(cleaned_steps)})
        return item

    def update_step(self, workflow_id: str, step_id: str, status: str, note: str = "") -> dict:
        if status not in STATUSES:
            raise ValueError(f"Unsupported status: {status}")
        items = self._read(self.path)
        for item in items:
            if item["id"] != workflow_id:
                continue
            for step in item["steps"]:
                if step["id"] != step_id:
                    continue
                previous = step["status"]
                step["status"] = status
                step["updated_at"] = self._now()
                if note.strip():
                    step["note"] = note.strip()
                statuses = [s["status"] for s in item["steps"]]
                if all(value == "COMPLETE" for value in statuses):
                    item["status"] = "COMPLETE"
                elif "FAILED" in statuses:
                    item["status"] = "FAILED"
                elif "BLOCKED_APPROVAL" in statuses:
                    item["status"] = "BLOCKED_APPROVAL"
                elif any(value == "IN_PROGRESS" for value in statuses):
                    item["status"] = "IN_PROGRESS"
                else:
                    item["status"] = "PLANNED"
                item["updated_at"] = self._now()
                self._write(self.path, items)
                self._audit("STEP_STATUS_CHANGED", {
                    "workflow_id": workflow_id,
                    "step_id": step_id,
                    "from": previous,
                    "to": status,
                    "note": note.strip(),
                })
                return item
        raise KeyError(f"Workflow or step not found: {workflow_id} / {step_id}")
