# ai_chain.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel as PydanticBaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnableLambda
import os

# ------------------ Load Environment Variables ------------------
from dotenv import load_dotenv
load_dotenv()  # 🔁 Ensure this runs early

# ------------------ LangSmith Tracing ------------------
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "CodeWhiz-AI-Project")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com").strip()
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")  # ✅ Explicitly set

# ------------------ LLM Init ------------------
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, timeout=30)

# ------------------ Structured Output Model ------------------
class AIResponse(PydanticBaseModel):
    explanation: str
    code: str

# Create parser
parser = PydanticOutputParser(pydantic_object=AIResponse)

# ------------------ Prompt Templates ------------------
prompts = {
    "explain": """Explain the following {lang} code in simple, beginner-friendly terms.
Focus on logic, performance, and potential issues.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' must be beginner-friendly.
- 'code' must be identical or slightly formatted for clarity.
- Return valid JSON only.
""",

    "refactor": """Refactor the following {lang} code to be cleaner, more efficient, and production-ready.
Add comments if needed.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' should describe improvements.
- 'code' must be idiomatic and clean.
- Return valid JSON only.
""",

    "fix": """Analyze this {lang} code and find bugs or performance issues.
Suggest fixes with explanations.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' must list bugs and fixes.
- 'code' should be corrected version.
- Return valid JSON only.
""",

    "doc": """Generate a professional {lang}-style docstring or comment block
for this function or class.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' should describe purpose.
- 'code' must include docstring.
- Return valid JSON only.
""",

    "test": """Generate unit tests for this {lang} function using the standard testing framework.
Include edge cases.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' should justify test cases.
- 'code' must be valid test code.
- Return valid JSON only.
""",

    "generate": """Generate {lang} code for this request:

{query}

Write clean, well-commented code.

{format_instructions}

IMPORTANT:
- 'explanation' must explain the logic.
- 'code' must contain ONLY the requested code, no extra text.
- NEVER include markdown code block delimiters (```) in 'code'.
- Return valid JSON only.
""",

    "chat": """You are CodeWhiz AI, a helpful coding assistant.
Respond to this query in context of {lang} development:

Query:
{query}

Code (if provided):
{code}

{format_instructions}

IMPORTANT:
- 'explanation' should answer the query clearly.
- 'code' should include code if relevant, else empty string.
- Return valid JSON only.
""",

    "translate": """Translate this {source_lang} code to {target_lang}.
Keep logic identical, but use idiomatic {target_lang} patterns.

Code:
{code}

{format_instructions}

IMPORTANT:
- 'explanation' should note key translation choices.
- 'code' must be valid {target_lang} code.
- Return valid JSON only.
""",
}

# ------------------ Chain Builder with Debug ------------------
def get_chain(feature: str):
    template = prompts.get(feature)
    if not template:
        raise ValueError(f"Unknown feature: {feature}")

    if feature == "generate":
        input_vars = ["query", "lang"]
    elif feature == "translate":
        input_vars = ["code", "source_lang", "target_lang"]
    elif feature == "chat":
        input_vars = ["query", "code", "lang"]
    else:
        input_vars = ["code", "lang"]

    prompt = PromptTemplate(
        template=template,
        input_variables=input_vars,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    # 🔍 Debug: Log the final prompt sent to LLM
    def debug_inputs(inputs):
        print(f"\n📝 [Chain: {feature}] Input to LLM:\n{prompt.format(**inputs)}\n")
        return inputs

    # Build chain
    return (
        RunnableLambda(debug_inputs) |
        prompt |
        llm |
        parser
    )