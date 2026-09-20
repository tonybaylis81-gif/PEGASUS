import os
import streamlit as st
from pegasus.core import Pegasus
from pegasus.portable import initialize_portable_root
from pegasus.vault_keeper import VaultKeeper

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

tabs = st.tabs(["Command", "VAULT KEEPER", "Records", "Documents", "Tasks", "Sentinels"])

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
    st.subheader("VAULT KEEPER")
    st.caption("Inventory and reconciliation operate automatically. Moves, renames, archival, and deletion are proposals only and require human authorization.")

    if not os.path.exists(vault_path):
        st.warning(f"Vault path does not exist yet: {vault_path}")
        st.info("Create the portable Vault directory or set PEGASUS_HOME to the portable root.")
    else:
        if st.button("INVENTORY VAULT", type="primary"):
            records = vault_keeper.inventory()
            st.success(f"Inventory complete. {len(records)} files registered.")
            st.rerun()

        report = vault_keeper.reconcile()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Registered", report["scanned_files"])
        c2.metric("Duplicate Groups", report["duplicate_groups"])
        c3.metric("Misfiled", len(report["misfiled_files"]))
        c4.metric("Numbering Drift", len(report["numbering_drift_candidates"]))

        search_term = st.text_input("Search Vault", placeholder="filename, project, Codex, patent...")
        if search_term.strip():
            st.dataframe(vault_keeper.search(search_term), use_container_width=True, hide_index=True)
        else:
            st.dataframe(vault_keeper.register(), use_container_width=True, hide_index=True)

        with st.expander("Reconciliation findings"):
            if report["duplicates"]:
                st.write("Duplicate groups")
                st.json(report["duplicates"])
            if report["misfiled_files"]:
                st.write("Files outside the controlled top-level sections")
                st.write(report["misfiled_files"])
            if report["numbering_drift_candidates"]:
                st.write("Numbering-drift candidates for human review")
                st.write(report["numbering_drift_candidates"])
            if not any((report["duplicates"], report["misfiled_files"], report["numbering_drift_candidates"])):
                st.success("No current reconciliation exceptions detected.")

        with st.expander("Human-authorized actions"):
            source = st.text_input("Source path")
            destination = st.text_input("Destination path (for moves/renames)")
            action = st.selectbox("Proposed action", ["MOVE", "RENAME", "ARCHIVE", "DELETE"])
            if st.button("Create Authorization Proposal"):
                if source.strip():
                    proposal = vault_keeper.propose_action(action, source.strip(), destination.strip() or None)
                    st.warning(f"Proposal {proposal['id']} is awaiting human authorization. No file was changed.")
                else:
                    st.warning("Enter a source path first.")

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
