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


def test_delegated_task_requires_explicit_authorization(tmp_path):
    p = Pegasus(str(tmp_path))
    task = p.create_task("Prepare prototype inspection", "Minion")
    assert task["status"] == "AWAITING_APPROVAL"
    assert task["authorization_status"] == "PENDING"

    import pytest
    with pytest.raises(PermissionError):
        p.update_task(task["id"], "IN_PROGRESS")

    approved = p.authorize_task(task["id"], "Founder / Human Authority")
    assert approved["authorization_status"] == "APPROVED"
    assert approved["status"] == "QUEUED"

    running = p.update_task(task["id"], "IN_PROGRESS")
    assert running["status"] == "IN_PROGRESS"

    with pytest.raises(ValueError):
        p.update_task(task["id"], "COMPLETE")

    complete = p.update_task(task["id"], "COMPLETE", "Inspection package prepared and checked.")
    assert complete["status"] == "COMPLETE"
    assert "Inspection package" in complete["result_note"]
