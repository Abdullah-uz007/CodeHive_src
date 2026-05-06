from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import json


load_dotenv()

_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm

prompt = ChatPromptTemplate.from_template("""
You are a senior Python debugger.

Fix the generated project for this project type:
{project_type}

STRICT RULES:
- Return ONLY valid JSON
- Fix ONLY necessary parts
- Keep code simple and runnable
- Do NOT add explanations
- Preserve the correct entry file:
  - app.py for Flask API and Streamlit App
  - main.py for CLI Tool, Machine Learning Script, and General Python Project
- Do not enable Flask debug mode or the reloader
- Avoid circular imports
- Keep requirements.txt minimal

Format:
{{
  "files": [
    {{
      "name": "file.py",
      "code": "fixed code"
    }}
  ]
}}

Code:
{code}

Error:
{error}
""")


def run_fix_agent(code, error, project_type: str = "General Python Project"):
    chain = prompt | get_llm()
    response = chain.invoke(
        {"code": json.dumps(code), "error": error, "project_type": project_type}
    )

    try:
        content = response.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except json.JSONDecodeError as exc:
        preview = response.content[:500].replace("\n", " ")
        raise ValueError(f"Fix agent returned invalid JSON: {preview}") from exc
