from pathlib import Path

from pegasus.core import Pegasus
from pegasus.portable import bootstrap_from_portable, initialize_portable_root


def test_portable_root_initializes(tmp_path: Path):
    root = tmp_path / "PEGASUS"
    result = initialize_portable_root(root)
    assert result["created"] is True
    assert (root / "LEDGER").is_dir()
    assert (root / "VAULT").is_dir()
    assert (root / "portable_manifest.json").is_file()


def test_pegasus_uses_portable_home(tmp_path: Path, monkeypatch):
    root = tmp_path / "PEGASUS"
    bootstrap_from_portable(root)
    monkeypatch.setenv("PEGASUS_HOME", str(root))
    p = Pegasus()
    p.create_record("Portable test", "Administrative")
    assert (root / "LEDGER" / "records.json").is_file()
    assert p.count("records") == 1
