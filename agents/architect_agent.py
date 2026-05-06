from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json


load_dotenv()

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
        )
    return _llm

prompt = ChatPromptTemplate.from_template("""
You are a senior software architect.

Design a clean, minimal Python project architecture for this project type:
{project_type}

Return ONLY JSON:
{{
  "architecture": {{
    "entry_file": "app.py",
    "files": [
      {{
        "name": "file_name.py",
        "purpose": "what it does"
      }}
    ],
    "notes": ["important implementation note"]
  }}
}}

Rules:
- Always include README.md and requirements.txt.
- Use app.py for Flask or Streamlit apps.
- Use main.py for CLI tools, ML scripts, and general Python projects.
- Avoid circular imports.
- Avoid placeholder files that are not needed by the request.
- Keep the architecture small enough to be runnable.

Plan:
{plan}

Research:
{research}
""")


def run_architect(plan: dict, research: dict, project_type: str = "General Python Project"):
    chain = prompt | get_llm()
    response = chain.invoke(
        {
            "plan": json.dumps(plan),
            "research": json.dumps(research),
            "project_type": project_type,
        }
    )

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {"architecture": {"entry_file": "main.py", "files": [response.content], "notes": []}}
