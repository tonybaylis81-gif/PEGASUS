from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


PORTABLE_DIRS = ("CORE", "VAULT", "LEDGER", "ARCHIVE", "BACKUPS", "PEGASUS_BOOTSTRAP")


def portable_root() -> Path:
    return Path(os.environ.get("PEGASUS_HOME", ".")).expanduser().resolve()


def initialize_portable_root(root: str | Path) -> dict:
    path = Path(root).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    for name in PORTABLE_DIRS:
        (path / name).mkdir(parents=True, exist_ok=True)
    manifest = path / "portable_manifest.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({
            "schema_version": 1,
            "system": "PEGASUS",
            "organization": "VALHALLA INDUSTRIAL UTILITY APPLICATIONS INC.",
            "purpose": "Portable administrative and command system",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ledger_path": "LEDGER",
            "vault_path": "VAULT/VALHALLA ENGINEERING VAULT",
            "human_authorization_required": True,
        }, indent=2), encoding="utf-8")
    return {"root": str(path), "created": True, "manifest": str(manifest)}


def bootstrap_from_portable(root: str | Path) -> dict:
    path = Path(root).expanduser().resolve()
    initialize_portable_root(path)
    os.environ["PEGASUS_HOME"] = str(path)
    return {
        "root": str(path),
        "ledger": str(path / "LEDGER"),
        "vault": str(path / "VAULT" / "VALHALLA ENGINEERING VAULT"),
        "ready": True,
    }


def backup_portable(root: str | Path, destination: str | Path) -> str:
    source = Path(root).expanduser().resolve()
    dest = Path(destination).expanduser().resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.make_archive(str(dest.with_suffix("")), "zip", root_dir=source)
    return str(dest.with_suffix(".zip"))
