from pegasus.core import Pegasus

def test_bootstrap(tmp_path):
    p = Pegasus(str(tmp_path))
    assert p.count("sentinels") == 1

def test_record_and_document(tmp_path):
    p = Pegasus(str(tmp_path))
    record = p.create_record("Test Record", "Engineering")
    document = p.register_document("Test Drawing", "Drawing", "Draft")
    assert record["id"].startswith("REC-")
    assert document["id"].startswith("DOC-")
    assert p.count("records") == 1
    assert p.count("documents") == 1

def test_task_requires_human_authorization_for_worker(tmp_path):
    p = Pegasus(str(tmp_path))
    task = p.create_task("Inspect prototype", "Sentinel Lieutenant")
    assert task["human_authorization_required"] is True
