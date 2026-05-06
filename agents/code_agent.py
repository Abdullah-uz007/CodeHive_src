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
            temperature=0.2,
        )
    return _llm

prompt = ChatPromptTemplate.from_template("""
You are a senior Python developer.

Generate clean, runnable code for this project type:
{project_type}

Rules:
- Return ONLY valid JSON
- No markdown
- No explanation
- Include requirements.txt with only necessary packages
- Include README.md with short run instructions
- Include a runnable entry file:
  - app.py for Flask API and Streamlit App
  - main.py for CLI Tool, Machine Learning Script, and General Python Project
- Do not enable Flask debug mode or the reloader
- Avoid circular imports
- Avoid fake placeholder modules
- Keep code simple and runnable without unavailable local files
- Add basic tests when practical

Output format MUST be:

{{
  "files": [
    {{
      "name": "app.py",
      "code": "print('hello')"
    }}
  ]
}}

Architecture:
{architecture}
""")


def run_code_agent(architecture: dict, project_type: str = "General Python Project"):
    chain = prompt | get_llm()
    response = chain.invoke(
        {"architecture": json.dumps(architecture), "project_type": project_type}
    )

    try:
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except json.JSONDecodeError as exc:
        preview = response.content[:500].replace("\n", " ")
        raise ValueError(f"Code agent returned invalid JSON: {preview}") from exc
