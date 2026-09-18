import os
import streamlit as st
from pegasus.core import Pegasus
from pegasus.portable import initialize_portable_root

st.set_page_config(page_title="PEGASUS", page_icon="🪽", layout="wide")

home = os.environ.get("PEGASUS_HOME")
if home:
    initialize_portable_root(home)
    pegasus = Pegasus()
else:
    pegasus = Pegasus()

st.title("🪽 PEGASUS")
st.caption("Valhalla Engineering Administrative & Command System")
st.divider()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Records", pegasus.count("records"))
col2.metric("Documents", pegasus.count("documents"))
col3.metric("Tasks", pegasus.count("tasks"))
col4.metric("Sentinels", pegasus.count("sentinels"))

st.caption(f"Portable home: {os.environ.get('PEGASUS_HOME', 'local project data')}")

tabs = st.tabs(["Command", "Records", "Documents", "Tasks", "Sentinels"])

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
    st.subheader("Record Ledger")
    st.dataframe(pegasus.list_items("records"), use_container_width=True, hide_index=True)
    with st.form("record_form"):
        title = st.text_input("Record title")
        category = st.selectbox("Category", ["Corporate", "Engineering", "Intellectual Property", "Project", "Test", "Financial", "Administrative"])
        submitted = st.form_submit_button("Create Record")
        if submitted and title.strip():
            item = pegasus.create_record(title.strip(), category)
            st.success(f"Record created: {item['id']}")

with tabs[2]:
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

with tabs[3]:
    st.subheader("Task Ledger")
    st.dataframe(pegasus.list_items("tasks"), use_container_width=True, hide_index=True)
    with st.form("task_form"):
        description = st.text_input("Task")
        assignee = st.selectbox("Authority", ["Pegasus", "Sentinel Lieutenant", "Minion", "Human"])
        submitted = st.form_submit_button("Create Task")
        if submitted and description.strip():
            item = pegasus.create_task(description.strip(), assignee)
            st.success(f"Task created: {item['id']}")

with tabs[4]:
    st.subheader("Chain of Command")
    st.markdown("""
    **PEGASUS** → administrative authority, records, filing, accounting, task orchestration  
    **SENTINEL LIEUTENANT** → delegated project/discipline command  
    **MINION** → parallel execution worker under a Sentinel  
    **HUMAN AUTHORITY** → required approval for consequential release and physical testing
    """)
    st.dataframe(pegasus.list_items("sentinels"), use_container_width=True, hide_index=True)
