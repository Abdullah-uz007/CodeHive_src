import json
import os
from pathlib import Path

import streamlit as st

from orchestration.controller import CodeHiveController, PROJECT_TYPES


st.set_page_config(page_title="CodeHive AI Dev System", layout="wide")
st.title("CodeHive AI Dev Engine")


def get_controller():
    if "controller" not in st.session_state:
        st.session_state.controller = CodeHiveController()
    return st.session_state.controller


def render_json(title, value):
    with st.expander(title, expanded=False):
        st.json(value or {})


def render_status(label, result):
    result = result or {}
    status = result.get("status", "unknown")
    if status in {"running", "installed", "created", "exists"}:
        st.success(f"{label}: {status}")
    elif status == "skipped":
        st.info(f"{label}: {status}")
    elif status == "error":
        st.error(f"{label}: {status}")
    else:
        st.warning(f"{label}: {status}")

    details = result.get("error") or result.get("reason")
    if details:
        st.code(details, language="text")


def render_generated_files(run_result):
    code = run_result.get("code") or {}
    files = code.get("files", [])
    st.subheader("Generated Files")
    if not files:
        st.info("No files generated yet.")
        return

    for generated_file in files:
        with st.expander(generated_file["name"], expanded=False):
            language = "python" if generated_file["name"].endswith(".py") else "text"
            st.code(generated_file["code"], language=language)


def render_project_browser(project_dir):
    st.subheader("Project Files")
    path = Path(project_dir) if project_dir else Path("generated_code")
    if not path.exists():
        st.info("No generated project folder found.")
        return

    st.caption(str(path))
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in {".venv", "__pycache__"}]
        for filename in files:
            file_path = Path(root) / filename
            if "__pycache__" in file_path.parts or file_path.suffix == ".pyc":
                continue
            relative = file_path.relative_to(path)
            with st.expander(str(relative), expanded=False):
                try:
                    language = "python" if file_path.suffix == ".py" else "text"
                    st.code(file_path.read_text(encoding="utf-8"), language=language)
                except UnicodeDecodeError:
                    st.info("Binary or non-UTF-8 file")


controller = get_controller()

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if "last_error" not in st.session_state:
    st.session_state.last_error = None

with st.sidebar:
    st.header("Build Settings")
    project_type = st.selectbox("Project type", PROJECT_TYPES, index=0)
    auto_install = st.checkbox(
        "Install generated dependencies",
        value=os.getenv("CODEHIVE_AUTO_INSTALL", "0") == "1",
    )
    os.environ["CODEHIVE_AUTO_INSTALL"] = "1" if auto_install else "0"

    if auto_install:
        st.caption("Dependencies install inside each generated project's .venv.")
    else:
        st.caption("Dependency install is skipped unless this is enabled.")

    if st.button("Stop Running Project"):
        controller.stop_process()
        st.success("Server stopped")

user_input = st.text_area("Enter your request", height=130)

run_btn = st.button("Run AI Pipeline", type="primary")

if run_btn:
    if not user_input.strip():
        st.warning("Enter a request first.")
    else:
        st.session_state.last_error = None
        with st.spinner("Running AI pipeline..."):
            try:
                st.session_state.last_result = controller.run(
                    user_input.strip(),
                    project_type=project_type,
                )
                st.success("Pipeline completed")
            except Exception as exc:
                st.session_state.last_error = str(exc)
                st.error(f"Pipeline failed: {exc}")

if st.session_state.last_error:
    st.error(st.session_state.last_error)

run_result = st.session_state.last_result

st.subheader("Server Status")
if controller.process and controller.process.poll() is None:
    st.success(f"Running at PID: {controller.process.pid}")
    st.info("http://127.0.0.1:5000")
else:
    st.warning("Server not running")

if run_result:
    c1, c2, c3 = st.columns(3)
    c1.metric("Project Type", run_result.get("project_type", "Unknown"))
    c2.metric("Generated Files", len((run_result.get("code") or {}).get("files", [])))
    c3.metric("Fix Attempts", len(run_result.get("fix_attempts") or []))

    st.caption(f"Project folder: {run_result.get('project_dir')}")

    tabs = st.tabs(["Pipeline", "Files", "Execution", "Raw"])

    with tabs[0]:
        render_json("Planner Output", run_result.get("plan"))
        render_json("Research Output", run_result.get("research"))
        render_json("Architecture Output", run_result.get("architecture"))

    with tabs[1]:
        render_generated_files(run_result)
        render_project_browser(run_result.get("project_dir"))

    with tabs[2]:
        render_status("Dependency install", run_result.get("install"))
        render_status("Execution", run_result.get("execution"))

        fix_attempts = run_result.get("fix_attempts") or []
        if fix_attempts:
            st.subheader("Fix Attempts")
            for attempt in fix_attempts:
                with st.expander(f"Attempt {attempt.get('number')} - {attempt.get('status')}"):
                    st.json(attempt)

    with tabs[3]:
        st.code(json.dumps(run_result, indent=2), language="json")
else:
    st.info("Choose a project type, enter a request, and run the pipeline.")
