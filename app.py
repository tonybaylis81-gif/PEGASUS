import os
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
from pegasus.core import Pegasus
from pegasus.portable import initialize_portable_root
from pegasus.vault_keeper import VaultKeeper
from pegasus.workflow import WorkflowLedger, STATUSES
from hydrogen_intel import scan_hydrogen, build_report
from vast_cash_monitor import run_vast_cash_sentinel, VAST_CASH_URL, VAST_CASH_REPO

st.set_page_config(page_title="PEGASUS", page_icon="🪽", layout="wide")

home = os.environ.get("PEGASUS_HOME")
if home:
    initialize_portable_root(home)
    pegasus = Pegasus()
    vault_path = os.path.join(home, "VAULT", "VALHALLA ENGINEERING VAULT")
    ledger_path = os.path.join(home, "LEDGER")
else:
    pegasus = Pegasus()
    vault_path = os.path.join("data", "VAULT", "VALHALLA ENGINEERING VAULT")
    ledger_path = os.path.join("data", "LEDGER")

Path(vault_path).mkdir(parents=True, exist_ok=True)
vault_keeper = VaultKeeper(vault_path, ledger_path)
workflow_ledger = WorkflowLedger(ledger_path)

# Hydrogen intelligence is scanned on demand from the web.
# The always-on background watcher is handled by GitHub Actions.
hydrogen_base = home or os.path.join("data")
if "hydrogen_scan" not in st.session_state:
    st.session_state.hydrogen_scan = {
        "scanned_at": "Not yet scanned",
        "articles": [],
        "errors": [],
        "feed_count": 0,
    }

if "vast_cash_sentinel" not in st.session_state:
    st.session_state.vast_cash_sentinel = None

def ingest_vault_zip(uploaded_zip):
    """Safely import a Vault ZIP without overwriting files already in PEGASUS."""
    target = Path(vault_path).resolve()
    target.mkdir(parents=True, exist_ok=True)
    if uploaded_zip.size > 500 * 1024 * 1024:
        raise ValueError("The ZIP file exceeds the 500 MB upload limit.")

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "vault.zip"
        zip_path.write_bytes(uploaded_zip.getbuffer())
        with zipfile.ZipFile(zip_path) as zf:
            members = zf.infolist()
            if len(members) > 10000:
                raise ValueError("Vault package contains too many entries.")
            total_uncompressed = sum(max(0, m.file_size) for m in members)
            if total_uncompressed > 500 * 1024 * 1024:
                raise ValueError("Vault package exceeds the 500 MB safety limit.")

            file_members = [m for m in members if not m.is_dir()]
            first_parts = [m.filename.replace("\\\\", "/").strip("/").split("/")[0] for m in file_members]
            strip_root = bool(first_parts) and all(
                part.casefold() == "valhalla engineering vault".casefold()
                for part in first_parts
            )

            planned = []
            for member in members:
                name = member.filename.replace("\\\\", "/").strip("/")
                parts = Path(name).parts
                if not name or name.startswith("/") or any(part in ("", ".", "..") for part in parts):
                    if name:
                        raise ValueError(f"Unsafe path in Vault package: {member.filename}")
                    continue
                if strip_root:
                    if len(parts) == 1:
                        continue
                    name = str(Path(*parts[1:]))
                destination = (target / name).resolve()
                if destination != target and target not in destination.parents:
                    raise ValueError(f"Unsafe destination in Vault package: {member.filename}")
                unix_mode = (member.external_attr >> 16) & 0o170000
                if unix_mode == 0o120000:
                    raise ValueError(f"Symbolic links are not allowed: {member.filename}")
                if not member.is_dir():
                    if destination.exists():
                        raise ValueError(
                            f"Import stopped to protect an existing file: {name}. "
                            "Nothing was overwritten."
                        )
                    planned.append((member, destination))
                else:
                    planned.append((member, destination))

            # All paths are checked before any file is written.
            for member, destination in planned:
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, destination.open("xb") as output:
                        output.write(source.read())

    return sum(1 for p in target.rglob("*") if p.is_file())

st.title("🪽 PEGASUS")
st.caption("Valhalla Engineering Administrative & Command System")
st.divider()

st.markdown("## UPLOAD YOUR VALHALLA ENGINEERING VAULT")
st.caption("Choose the ZIP downloaded from Google Drive, or drag and drop it into the area below. Your Google Drive original is not changed.")
vault_upload = st.file_uploader(
    "Drop your Vault ZIP here, or browse files",
    type=["zip"],
    key="main_vault_zip_upload",
)
if st.button(
    "⬆️  IMPORT VAULT INTO PEGASUS",
    type="primary",
    use_container_width=True,
    disabled=vault_upload is None,
    key="main_import_vault",
):
    try:
        with st.spinner("PEGASUS is safely importing your Vault..."):
            imported_count = ingest_vault_zip(vault_upload)
            refreshed = vault_keeper.inventory()
        st.success(f"Vault import complete. {imported_count} files are now in PEGASUS. {len(refreshed)} files registered.")
        st.rerun()
    except Exception as exc:
        st.error(f"Vault import stopped: {exc}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", pegasus.count("records"))
col2.metric("Documents", pegasus.count("documents"))
col3.metric("Tasks", pegasus.count("tasks"))
col4.metric("Sentinels", pegasus.count("sentinels"))
col5.metric("Vault Files", len(vault_keeper.register()))

st.caption(f"Portable home: {os.environ.get('PEGASUS_HOME', 'local project data')}")

tabs = st.tabs(["Command", "HYDROGEN INTELLIGENCE", "Records", "Documents", "Tasks", "Sentinels", "VAULT KEEPER", "Workflows"])

with tabs[0]:
    st.subheader("Command Console")
    st.info("Pegasus is the administrative authority and record keeper. Operational release remains subject to human authorization.")
    command = st.text_area("Command / instruction", placeholder="Enter a task, directive, or administrative instruction...")
    if st.button("Log Command", type="primary"):
        if command.strip():
            item = pegasus.log_command(command.strip())
            st.success(f"Command logged: {item['id']}")
        else:
            st.warning("Enter a command first.")

    st.divider()
    st.subheader("⚒️ VAST CASH COMMAND & SENTINEL")
    st.caption("Pegasus can launch the VAST CASH web application and perform a read-only health check of the application, GitHub repository, and optional Alpaca PAPER account.")
    vc1, vc2 = st.columns(2)
    with vc1:
        st.link_button("🚀 OPEN / RUN VAST CASH", VAST_CASH_URL, use_container_width=True)
        st.caption(f"VAST CASH application: {VAST_CASH_URL}")
    with vc2:
        if st.button("🛡️ RUN VAST CASH SENTINEL", type="primary", use_container_width=True):
            with st.spinner("PEGASUS is checking VAST CASH..."):
                st.session_state.vast_cash_sentinel = run_vast_cash_sentinel()

    sentinel = st.session_state.vast_cash_sentinel
    if sentinel:
        state = sentinel["state"]
        if state == "GREEN":
            st.success("🟢 VAST CASH SENTINEL: GREEN")
        elif state == "AMBER":
            st.warning("🟡 VAST CASH SENTINEL: AMBER")
        else:
            st.error("🔴 VAST CASH SENTINEL: RED")

        web = sentinel["web"]
        gh = sentinel["github"]
        paper = sentinel["paper"]
        a, b, c = st.columns(3)
        a.metric("VAST CASH WEB", "ONLINE" if web["online"] else "OFFLINE")
        b.metric("VAST CASH CODE", gh.get("sha") or "UNAVAILABLE")
        if paper.get("configured") and paper.get("connected"):
            c.metric("PAPER API", "CONNECTED")
        elif paper.get("configured"):
            c.metric("PAPER API", "ERROR")
        else:
            c.metric("PAPER API", "NOT CONFIGURED")

        with st.expander("VAST CASH Sentinel details"):
            st.write({
                "Web monitor": web,
                "GitHub monitor": gh,
                "Alpaca PAPER monitor": paper,
                "Repository": VAST_CASH_REPO,
            })
    else:
        st.info("VAST CASH Sentinel has not been run yet.")

with tabs[1]:
    st.subheader("VALHALLA HYDROGEN COMMAND")
    st.caption("PEGASUS is launched on the World Wide Web through Streamlit. The background hydrogen watch runs independently through GitHub Actions.")

    # Remote watcher controls. Set these in Streamlit Secrets:
    # GITHUB_TOKEN = a GitHub token with Actions write access to this repository.
    github_token = st.secrets.get("GITHUB_TOKEN", "")
    repo = st.secrets.get("GITHUB_REPOSITORY", "tonybaylis81-gif/PEGASUS")
    workflow_file = "hydrogen-watch.yml"

    online_col, alert_col = st.columns(2)
    online_col.success("🟢 PEGASUS WEB CONTROL: ONLINE")
    if github_token:
        alert_col.success("🟢 HYDROGEN WATCH: REMOTE CONTROL ENABLED")
    else:
        alert_col.warning("🟡 HYDROGEN WATCH: add GITHUB_TOKEN to Streamlit Secrets for remote launch")

    if github_token:
        if st.button("🚀 LAUNCH HYDROGEN WATCH NOW", type="primary"):
            import json
            import urllib.request

            url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_file}/dispatches"
            payload = json.dumps({"ref": "main"}).encode()
            request = urllib.request.Request(
                url,
                data=payload,
                method="POST",
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "Content-Type": "application/json",
                    "User-Agent": "PEGASUS-Valhalla-Web-Control/1.0",
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    if response.status == 204:
                        st.success("🚀 PEGASUS HYDROGEN WATCH LAUNCHED. GitHub is now running the scan.")
                    else:
                        st.warning(f"GitHub accepted the request with HTTP {response.status}.")
            except Exception as exc:
                st.error(f"Launch failed: {exc}")

    st.markdown("### Local Intelligence Console")
    scan = st.session_state.hydrogen_scan
    if scan["articles"]:
        st.info(f"Showing the latest local scan: {scan['scanned_at']}")
    else:
        st.info("No local scan has been run yet. The background GitHub watcher remains independent.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Items collected", len(scan["articles"]))
    c2.metric("Sources scanned", scan["feed_count"])
    c3.metric("Source errors", len(scan["errors"]))

    if st.button("SCAN HYDROGEN FROM WEB NOW"):
        with st.spinner("PEGASUS is scanning hydrogen intelligence sources..."):
            st.session_state.hydrogen_scan = scan_hydrogen()
        st.rerun()

    report_markdown = build_report(scan)
    st.markdown("### READABLE VALHALLA HYDROGEN REPORT")
    st.caption("Click OPEN SOURCE on any intelligence item to read the original source.")
    with st.container(border=True):
        st.markdown(report_markdown, unsafe_allow_html=False)

    st.download_button(
        "DOWNLOAD CURRENT VALHALLA HYDROGEN REPORT",
        report_markdown,
        "VALHALLA_HYDROGEN_REPORT.md",
        "text/markdown",
    )

    st.markdown("### Latest Hydrogen Intelligence")
    st.dataframe(scan["articles"], use_container_width=True, hide_index=True)

    if scan["errors"]:
        with st.expander("Source connection errors"):
            st.write(scan["errors"])

    st.markdown("### Archived Reports")
    report_dir = Path(hydrogen_base) / "HYDROGEN_REPORTS"
    if report_dir.exists():
        reports = sorted(report_dir.glob("VHR_*.md"), reverse=True)
        for report_path in reports[:20]:
            st.write(report_path.name)

with tabs[2]:
    st.subheader("Record Ledger")
    st.dataframe(pegasus.list_items("records"), use_container_width=True, hide_index=True)
    with st.form("record_form"):
        title = st.text_input("Record title")
        category = st.selectbox("Category", ["Corporate", "Engineering", "Intellectual Property", "Project", "Test", "Financial", "Administrative"])
        submitted = st.form_submit_button("Create Record")
        if submitted and title.strip():
            item = pegasus.create_record(title.strip(), category)
            st.success(f"Record created: {item['id']}")

with tabs[3]:
    st.subheader("Document Accountant")
    st.caption("Documents receive stable identifiers, categories, status, and provenance.")
    st.dataframe(pegasus.list_items("documents"), use_container_width=True, hide_index=True)
    with st.form("document_form"):
        title = st.text_input("Document title")
        category = st.selectbox("Document category", ["Drawing", "Specification", "Report", "Patent", "Policy", "Procedure", "Correspondence", "Other"])
        status = st.selectbox("Status", ["Draft", "Review", "Approved", "Superseded", "Archived"])
        submitted = st.form_submit_button("Register Document")
        if submitted and title.strip():
            item = pegasus.register_document(title.strip(), category, status)
            st.success(f"Document registered: {item['id']}")

with tabs[4]:
    st.subheader("Task Ledger")
    st.dataframe(pegasus.list_items("tasks"), use_container_width=True, hide_index=True)
    with st.form("task_form"):
        description = st.text_input("Task")
        assignee = st.selectbox("Authority", ["Pegasus", "Sentinel Lieutenant", "Minion", "Human"])
        submitted = st.form_submit_button("Create Task")
        if submitted and description.strip():
            item = pegasus.create_task(description.strip(), assignee)
            st.success(f"Task created: {item['id']}")

with tabs[5]:
    st.subheader("Chain of Command")
    st.markdown("""
    **PEGASUS** → administrative authority, records, filing, accounting, task orchestration  
    **SENTINEL LIEUTENANT** → delegated project/discipline command  
    **MINION** → parallel execution worker under a Sentinel  
    **HUMAN AUTHORITY** → required approval for consequential release and physical testing
    """)
    st.dataframe(pegasus.list_items("sentinels"), use_container_width=True, hide_index=True)


with tabs[6]:
    st.subheader("VALHALLA ENGINEERING VAULT")
    st.caption("Inventory, verify, search and reconcile the Vault. PEGASUS does not move, rename or delete Vault files without human authorization.")

    action_col, reconcile_col = st.columns(2)
    if action_col.button("SCAN / REFRESH VAULT INVENTORY", type="primary", use_container_width=True):
        with st.spinner("PEGASUS is hashing and registering Vault files..."):
            inventory = vault_keeper.inventory()
        st.success(f"Vault inventory refreshed: {len(inventory)} files registered.")
        st.rerun()

    if reconcile_col.button("RUN VAULT RECONCILIATION", use_container_width=True):
        with st.spinner("Checking duplicates, filing sections and numbering candidates..."):
            report = vault_keeper.reconcile()
        st.session_state["vault_reconciliation"] = report

    if "vault_reconciliation" in st.session_state:
        st.markdown("### Reconciliation report")
        st.json(st.session_state["vault_reconciliation"])

    st.markdown("### Search registered files")
    search_term = st.text_input("Filename or folder term", key="vault_search_term")
    if search_term.strip():
        matches = vault_keeper.search(search_term)
        st.dataframe(matches, use_container_width=True, hide_index=True)
        if not matches:
            st.info("No matching files in the current register.")

    st.markdown("### Registered Vault files")
    registered_files = vault_keeper.register()
    if registered_files:
        st.dataframe(registered_files, use_container_width=True, hide_index=True)
    else:
        st.info("No files have been registered yet. Run SCAN / REFRESH VAULT INVENTORY after connecting or importing the Vault.")

with tabs[7]:
    st.subheader("Goal-to-Completion Workflows")
    st.caption(
        "Record a goal, break it into ordered steps, track progress, and keep an audit trail. "
        "Creating a workflow records a plan only; it does not execute external actions."
    )

    with st.form("workflow_create_form", clear_on_submit=True):
        workflow_goal = st.text_input("Goal / desired outcome", placeholder="Example: Prepare the next hydrogen commercialization research brief")
        workflow_steps_text = st.text_area(
            "Steps (one per line, in order)",
            placeholder="Collect current sources\nCompare technical claims\nDraft findings\nReview sources and uncertainties",
            height=150,
        )
        workflow_owner = st.selectbox("Workflow lead", ["Pegasus", "Sentinel Lieutenant", "Human"])
        workflow_submit = st.form_submit_button("Create Workflow Plan", type="primary")

    if workflow_submit:
        steps = workflow_steps_text.splitlines()
        try:
            created = workflow_ledger.create(workflow_goal, steps, workflow_owner)
            st.success(f"Workflow plan created: {created['id']}")
            st.info("Plan recorded only. No external actions were executed.")
        except ValueError as exc:
            st.error(str(exc))

    workflows = workflow_ledger.list_workflows()
    st.markdown("### Workflow Register")
    if workflows:
        summary = [
            {
                "ID": item["id"],
                "Goal": item["goal"],
                "Lead": item["owner"],
                "Status": item["status"],
                "Steps": len(item["steps"]),
                "Completed": sum(1 for step in item["steps"] if step["status"] == "COMPLETE"),
                "Updated": item["updated_at"],
            }
            for item in workflows
        ]
        st.dataframe(summary, use_container_width=True, hide_index=True)

        workflow_options = {f"{item['id']} | {item['goal']}": item for item in workflows}
        selected_label = st.selectbox("Select workflow to inspect", list(workflow_options.keys()))
        selected_workflow = workflow_options[selected_label]
        st.markdown(f"#### {selected_workflow['id']}: {selected_workflow['goal']}")
        st.caption(selected_workflow.get("execution_note", ""))
        st.dataframe(selected_workflow["steps"], use_container_width=True, hide_index=True)

        step_options = {
            f"{step['id']} | {step['description']} [{step['status']}]": step
            for step in selected_workflow["steps"]
        }
        with st.form("workflow_step_update_form"):
            selected_step_label = st.selectbox("Step to update", list(step_options.keys()))
            selected_status = st.selectbox("New status", list(STATUSES))
            update_note = st.text_input("Update note (optional)")
            step_submit = st.form_submit_button("Record Step Update")
        if step_submit:
            chosen_step = step_options[selected_step_label]
            try:
                workflow_ledger.update_step(
                    selected_workflow["id"], chosen_step["id"], selected_status, update_note
                )
                st.success("Step status and audit trail updated.")
                st.rerun()
            except (ValueError, KeyError) as exc:
                st.error(str(exc))

        with st.expander("Workflow audit trail"):
            audit_path = Path(ledger_path) / "workflow_audit.json"
            if audit_path.exists():
                import json
                audit_entries = json.loads(audit_path.read_text(encoding="utf-8"))
                matching = [
                    event for event in reversed(audit_entries)
                    if event.get("details", {}).get("workflow_id") == selected_workflow["id"]
                ]
                st.dataframe(matching, use_container_width=True, hide_index=True)
    else:
        st.info("No workflow plans yet. Create one above to begin.")
