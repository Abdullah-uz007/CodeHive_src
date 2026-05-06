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
You are an expert AI planner.

Break the user's request into a practical implementation plan for this project type:
{project_type}

Return ONLY valid JSON in this format:
{{
  "project_type": "{project_type}",
  "summary": "one sentence summary",
  "steps": ["step 1", "step 2", "step 3"],
  "acceptance_criteria": ["criterion 1", "criterion 2"]
}}

Rules:
- Keep the plan focused and buildable.
- Avoid unnecessary features and dependencies.
- Include testing or manual verification as a final step.

User Request:
{input}
""")


def run_planner(user_input: str, project_type: str = "General Python Project"):
    chain = prompt | get_llm()
    response = chain.invoke({"input": user_input, "project_type": project_type})

    try:
        return json.loads(response.content)
    except json.JSONDecodeError:
        return {
            "project_type": project_type,
            "summary": user_input,
            "steps": [response.content],
            "acceptance_criteria": [],
        }
