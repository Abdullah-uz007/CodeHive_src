from agents.architect_agent import run_architect
from agents.code_agent import run_code_agent
from agents.fix_agent import run_fix_agent
from agents.planner_agent import run_planner
from agents.research_agent import run_research

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


PROJECT_TYPES = [
    "Flask API",
    "Streamlit App",
    "CLI Tool",
    "Machine Learning Script",
    "General Python Project",
]


class CodeHiveController:
    def __init__(self, project_root=None):
        self.project_root = Path(project_root or os.getcwd()).resolve()
        self.projects_root = self.project_root / "generated_projects"
        self.latest_dir = self.project_root / "generated_code"
        self.generated_dir = self.latest_dir
        self.process = None
        self.last_result = None
        self.last_execution_result = None
        self.last_install_result = None

    def log(self, msg):
        print(f"\n[CodeHive] {msg}")

    # ---------------- MAIN RUN ----------------

    def run(self, user_input: str, project_type: str = "General Python Project"):
        if project_type not in PROJECT_TYPES:
            project_type = "General Python Project"

        self._header(user_input, project_type)
        self.generated_dir = self._create_project_dir(project_type)

        run_result = {
            "request": user_input,
            "project_type": project_type,
            "project_dir": str(self.generated_dir),
            "plan": None,
            "research": None,
            "architecture": None,
            "code": None,
            "install": None,
            "execution": None,
            "fix_attempts": [],
        }

        plan = self.planner_step(user_input, project_type)
        run_result["plan"] = plan

        research = self.research_step(plan, project_type)
        run_result["research"] = research

        architecture = self.architect_step(plan, research, project_type)
        run_result["architecture"] = architecture

        code = self.code_step(architecture, project_type)
        run_result["code"] = code
        self._sync_latest_project()

        install_result = self.install_dependencies()
        run_result["install"] = install_result
        self.last_install_result = install_result

        if install_result.get("status") == "error":
            execution_result = install_result
        else:
            execution_result = self.execute_step(code)
            code, execution_result, fix_attempts = self.qa_loop(code, execution_result, project_type)
            run_result["code"] = code
            run_result["fix_attempts"] = fix_attempts
            self._sync_latest_project()

        run_result["execution"] = execution_result
        self.last_execution_result = execution_result
        self.last_result = run_result

        self.pretty_print(run_result)

        print("\nFINAL OUTPUT READY\n")
        return run_result

    # ---------------- UI ----------------

    def _header(self, user_input, project_type):
        print("\n" + "=" * 60)
        print("CODEHIVE PIPELINE STARTED")
        print("=" * 60)
        print(f"\nPROJECT TYPE: {project_type}")
        print(f"USER INPUT: {user_input}\n")

    # ---------------- AGENTS ----------------

    def planner_step(self, user_input, project_type):
        self.log("Planner Agent Running")
        return run_planner(user_input, project_type)

    def research_step(self, plan, project_type):
        self.log("Research Agent Running")
        return run_research(plan, project_type)

    def architect_step(self, plan, research, project_type):
        self.log("Architect Agent Running")
        result = run_architect(plan, research, project_type)

        try:
            text = result["architecture"]["files"][0]
            if isinstance(text, str):
                cleaned = re.sub(r"```json|```", "", text).strip()
                return json.loads(cleaned)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            pass

        return result

    def code_step(self, architecture, project_type):
        self.log("Code Agent Running")
        result = run_code_agent(architecture, project_type)
        self._validate_code_result(result)
        self._write_files(result)
        return result

    # ---------------- PROJECT WORKSPACES ----------------

    def _create_project_dir(self, project_type):
        self.projects_root.mkdir(exist_ok=True)
        slug = self._slugify(project_type)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base = self.projects_root / f"{timestamp}_{slug}"
        project_dir = base
        counter = 2
        while project_dir.exists():
            project_dir = Path(f"{base}_{counter}")
            counter += 1
        project_dir.mkdir(parents=True)
        return project_dir.resolve()

    def _sync_latest_project(self):
        if self.latest_dir.exists():
            shutil.rmtree(self.latest_dir)
        shutil.copytree(
            self.generated_dir,
            self.latest_dir,
            ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc"),
        )

    def _slugify(self, value):
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "project"

    # ---------------- EXECUTION ----------------

    def execute_step(self, code):
        self.log("Execution Engine Running")

        try:
            entry = self._find_entry_file(code)
            if entry is None:
                return {
                    "status": "skipped",
                    "reason": "No runnable entry file found. Expected app.py, main.py, or cli.py.",
                }

            self.stop_process()

            python_exe = self._project_python()
            env = os.environ.copy()
            env.setdefault("PYTHONUNBUFFERED", "1")

            self.process = subprocess.Popen(
                [str(python_exe), str(entry)],
                cwd=str(self.generated_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            time.sleep(1.5)

            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate(timeout=5)
                return {
                    "status": "error",
                    "entry": entry.name,
                    "stdout": stdout.strip(),
                    "error": stderr.strip() or "Process exited without stderr.",
                }

            return {"status": "running", "entry": entry.name, "pid": self.process.pid}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _find_entry_file(self, code):
        names = []
        for file in code.get("files", []):
            if isinstance(file, dict) and file.get("name"):
                names.append(Path(file["name"]).as_posix())

        for entry_name in ("app.py", "main.py", "cli.py"):
            if entry_name in names:
                entry = self.generated_dir / entry_name
                if entry.exists():
                    return entry

        return None

    def _project_python(self):
        candidate = self._project_venv_python()
        return candidate if candidate.exists() else Path(sys.executable)

    def _project_venv_python(self):
        venv_dir = self.generated_dir / ".venv"
        if os.name == "nt":
            return venv_dir / "Scripts" / "python.exe"
        return venv_dir / "bin" / "python"

    def stop_process(self):
        if not self.process:
            return

        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)

        self.process = None

    # ---------------- QA LOOP ----------------

    def qa_loop(self, code, execution_result, project_type):
        self.log("QA Agent Running")

        retries = 0
        max_retries = 3
        fix_attempts = []

        while execution_result.get("status") == "error" and retries < max_retries:
            attempt = {
                "number": retries + 1,
                "input_error": execution_result.get("error", ""),
                "status": "started",
            }
            fix_attempts.append(attempt)

            self.log(f"Error Detected. Attempting Fix {retries + 1}/{max_retries}...")
            self.log(f"Traceback: {execution_result.get('error', '')[:200]}...")

            try:
                fixed = run_fix_agent(code, execution_result.get("error", ""), project_type)
                self._validate_code_result(fixed)
            except Exception as exc:
                attempt["status"] = "failed"
                attempt["error"] = str(exc)
                self.log(f"Fix Agent failed: {exc}")
                break

            self._write_files(fixed)
            code = fixed
            execution_result = self.execute_step(code)
            attempt["status"] = execution_result.get("status", "unknown")
            attempt["execution"] = execution_result
            retries += 1

        return code, execution_result, fix_attempts

    # ---------------- FILE WRITER ----------------

    def _validate_code_result(self, code):
        if not isinstance(code, dict):
            raise ValueError("Code agent response must be a dictionary.")

        files = code.get("files")
        if not isinstance(files, list) or not files:
            raise ValueError("Code agent response must include a non-empty files list.")

        for file in files:
            if not isinstance(file, dict):
                raise ValueError("Each generated file entry must be a dictionary.")
            if not isinstance(file.get("name"), str) or not file["name"].strip():
                raise ValueError("Each generated file needs a non-empty name.")
            if not isinstance(file.get("code"), str):
                raise ValueError(f"Generated file {file.get('name')} needs string code.")
            self._safe_generated_path(file["name"])

    def _safe_generated_path(self, filename):
        candidate = Path(filename)
        if candidate.is_absolute():
            raise ValueError(f"Absolute generated paths are not allowed: {filename}")
        if any(part in {"", ".", ".."} for part in candidate.parts):
            raise ValueError(f"Unsafe generated path is not allowed: {filename}")

        target = (self.generated_dir / candidate).resolve()
        try:
            target.relative_to(self.generated_dir.resolve())
        except ValueError as exc:
            raise ValueError(f"Generated path escapes project directory: {filename}") from exc

        return target

    def _write_files(self, code):
        self.generated_dir.mkdir(exist_ok=True)

        for file in code["files"]:
            path = self._safe_generated_path(file["name"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(file["code"], encoding="utf-8")

    # ---------------- DEPENDENCIES ----------------

    def install_dependencies(self):
        req_path = self.generated_dir / "requirements.txt"

        if not req_path.exists():
            return {"status": "skipped", "reason": "No generated requirements.txt found."}

        clean = self._read_requirements(req_path)
        if not clean:
            return {"status": "skipped", "reason": "Generated requirements.txt was empty."}

        if os.getenv("CODEHIVE_AUTO_INSTALL", "0") != "1":
            self.log("Dependency install skipped. Set CODEHIVE_AUTO_INSTALL=1 to enable it.")
            return {
                "status": "skipped",
                "reason": "Automatic dependency installation is disabled.",
                "dependencies": clean,
            }

        venv_result = self._ensure_project_venv()
        if venv_result.get("status") == "error":
            return venv_result

        python_exe = self._project_python()
        self.log("Installing dependencies into the generated project's virtual environment...")
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", *clean],
            cwd=str(self.generated_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr.strip() or result.stdout.strip() or "pip install failed.",
                "dependencies": clean,
                "venv": str(self.generated_dir / ".venv"),
            }

        return {
            "status": "installed",
            "dependencies": clean,
            "venv": str(self.generated_dir / ".venv"),
        }

    def _read_requirements(self, req_path):
        clean = []
        for dep in req_path.read_text(encoding="utf-8").splitlines():
            dep = dep.strip()
            if not dep or dep.startswith("#"):
                continue
            if dep.lower() == "flask":
                clean.append("Flask==2.3.3")
            else:
                clean.append(dep)
        return clean

    def _ensure_project_venv(self):
        venv_dir = self.generated_dir / ".venv"
        if self._project_venv_python().exists():
            return {"status": "exists", "venv": str(venv_dir)}

        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            cwd=str(self.generated_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return {
                "status": "error",
                "error": result.stderr.strip() or result.stdout.strip() or "venv creation failed.",
            }

        return {"status": "created", "venv": str(venv_dir)}

    # ---------------- OUTPUT ----------------

    def pretty_print(self, run_result):
        print("\n" + "=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        print(f"\nPROJECT TYPE: {run_result['project_type']}")
        print(f"PROJECT DIR: {run_result['project_dir']}")

        print("\nPLAN:")
        for i, step in enumerate(run_result["plan"].get("steps", []), 1):
            print(f"{i}. {step}")

        print("\nFILES GENERATED:")
        for f in run_result["code"].get("files", []):
            print(f"  - {f['name']}")

        install_result = run_result["install"] or {}
        execution_result = run_result["execution"] or {}
        print(f"\nDEPENDENCIES: {install_result.get('status', 'unknown').upper()}")
        print(f"FINAL STATUS: {execution_result.get('status', 'unknown').upper()}")
        if execution_result.get("pid"):
            print(f"PID: {execution_result['pid']}")

        print("=" * 60)
