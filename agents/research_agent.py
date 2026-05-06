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
You are an expert AI researcher for Python projects.

Project type:
{project_type}

Based on the plan, recommend only the minimal libraries, frameworks, and tools
needed to build the request.

Return ONLY JSON:
{{
  "tools": ["tool1", "tool2"],
  "dependencies": ["package==version or package>=version"],
  "avoid": ["unnecessary package or pattern"],
  "reasoning": "short explanation"
}}

Rules:
- Keep dependencies minimal.
- Prefer the Python standard library when it is enough.
- For Flask APIs, include Flask.
- For Streamlit apps, include Streamlit.
- For CLI tools, avoid web frameworks unless the user asks for one.

Plan:
{plan}
""")


def run_research(plan: dict, project_type: str = "General Python Project"):
    chain = prompt | get_llm()
    response = chain.invoke({"plan": json.dumps(plan), "project_type": project_type})

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "tools": [],
            "dependencies": [],
            "avoid": [],
            "reasoning": response.content,
        }
