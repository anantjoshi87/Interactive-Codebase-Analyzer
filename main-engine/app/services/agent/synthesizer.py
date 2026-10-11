from typing import Any, Dict
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.agent.state import AgentState

SYNTHESIZER_SYSTEM_PROMPT = """You are a Senior Principal Software Engineer.
Answer the developer's question thoroughly using only the verified facts, symbol definitions,
call graphs, and code snippets provided.

Requirements:
- Ground every technical claim in the retrieved facts.
- Explicitly cite file locations, symbol names, and line ranges where applicable.
- If comparing implementations, use clear side-by-side breakdowns or markdown tables.
- For architectural flow traces, provide the sequential call chain clearly (A -> B -> C).
"""


async def synthesizer_node(state: AgentState) -> Dict[str, Any]:
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )

    evidence_blocks = []
    for item in state.get("gathered_context", []):
        evidence_blocks.append(
            f"### Result from {item.get('tool')} (Task {item.get('task_id')}):\n"
            f"```json\n{item.get('data')}\n```"
        )

    full_context = (
        "\n\n".join(evidence_blocks) if evidence_blocks else "No context retrieved."
    )

    user_prompt = f"""Developer Question:
        {state['query']}

        Retrieved Repository Evidence:
        {full_context}
        """

    response = await llm.ainvoke(
        [
            {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    return {"final_answer": response.content}
