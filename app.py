import os
import tempfile
import zipfile
from pathlib import Path

import streamlit as st
from pegasus.core import Pegasus
from pegasus.portable import initialize_portable_root
from pegasus.vault_keeper import VaultKeeper
from hydrogen_intel import scan_hydrogen, build_report

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

vault_keeper = VaultKeeper(vault_path, ledger_path)

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

def ingest_vault_zip(uploaded_zip):
    """Safely unpack a user-supplied Vault ZIP into PEGASUS working storage."""
    target = Path(vault_path).resolve()
    target.mkdir(parents=True, exist_ok=True)
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
            for member in members:
                name = member.filename.replace("\\\\", "/")
                if name.startswith("/") or any(part == ".." for part in Path(name).parts):
                    raise ValueError(f"Unsafe path in Vault package: {member.filename}")
                destination = (target / name).resolve()
                if destination != target and target not in destination.parents:
                    raise ValueError(f"Unsafe destination in Vault package: {member.filename}")
            zf.extractall(target)
    return sum(1 for p in target.rglob("*") if p.is_file())

st.title("🪽 PEGASUS")
st.caption("Valhalla Engineering Administrative & Command System")
st.divider()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Records", pegasus.count("records"))
col2.metric("Documents", pegasus.count("documents"))
col3.metric("Tasks", pegasus.count("tasks"))
col4.metric("Sentinels", pegasus.count("sentinels"))
col5.metric("Vault Files", len(vault_keeper.register()))

st.caption(f"Portable home: {os.environ.get('PEGASUS_HOME', 'local project data')}")

tabs = st.tabs(["Command", "HYDROGEN INTELLIGENCE", "VAULT KEEPER", "Records", "Documents", "Tasks", "Sentinels"])

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
