# CodeHive 🐝

![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/built%20with-Streamlit-ff4b4b?style=flat-square)
![LangChain](https://img.shields.io/badge/agents-LangChain-1c1c1c?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

**AI-assisted Python project generator.** Describe what you want to build — CodeHive runs it through a multi-agent pipeline (Planner → Researcher → Architect → Coder → Fixer) and spits out a structured, runnable Python project.

---

## About

CodeHive is a multi-agent AI system built with LangChain and GPT-4o. You give it a project idea, and 5 specialized agents handle the rest — planning, researching, designing the architecture, writing the code, and fixing any errors that come up at runtime.

The Fix agent loops until the code runs clean, so you're not just getting a code dump — you're getting something that's actually been tested.

Built this to explore how far you can push agentic workflows for real developer tasks, not just toy demos.

---

## What It Does

Each run generates a timestamped project folder under `generated_projects/` and also refreshes `generated_code/` as a copy of the latest output.

You pick a project type before generation, and every agent adapts its output accordingly:

- Flask API
- Streamlit App
- CLI Tool
- Machine Learning Script
- General Python Project

---

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your OpenAI API key
cp .env.example .env
# then open .env and fill in OPENAI_API_KEY
```

**Run the UI:**
```bash
streamlit run ui.py
```

**Or use the CLI:**
```bash
python main.py
```

---

## UI Dashboard

The Streamlit interface walks you through the full pipeline and shows:

- Planner output
- Research output
- Architecture output
- Generated files with code preview
- Dependency install status
- Runtime output
- Fix attempts (if any)
- Generated project folder contents

---

## Dependency Installation

By default, CodeHive **does not** install the generated project's dependencies into your environment. This is intentional — it keeps things clean.

**In the UI:** Toggle "Install generated dependencies" to have CodeHive create a `.venv` inside the generated project folder and install its requirements there.

**In the CLI:**
```bash
# Windows PowerShell
$env:CODEHIVE_AUTO_INSTALL = "1"

# macOS/Linux
export CODEHIVE_AUTO_INSTALL=1
```

---

## Agent Pipeline

```
User Prompt + Project Type
        ↓
   [Planner Agent]       — breaks down the task
        ↓
  [Research Agent]       — identifies tools, libraries, patterns
        ↓
 [Architecture Agent]    — designs project structure
        ↓
    [Code Agent]         — generates all files
        ↓
    [Fix Agent]          — loops until the code runs clean
        ↓
  generated_projects/
```

---

## .gitignore Checklist

Make sure these are excluded before pushing:

```
.env
venv/
.venv/
__pycache__/
generated_projects/**/.venv/
```
