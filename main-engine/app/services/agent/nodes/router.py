from typing import Any, Dict
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.agent.state import AgentState, QueryStrategy, RouterDecision, SubTask

ROUTER_SYSTEM_PROMPT = """You are the Senior Routing Architect for an Agentic Codebase Intelligence Engine.
Analyze the user query and classify it into an execution strategy.

STRATEGY SELECTION CRITERIA:
1. 'flow_trace': ONLY select this if the user EXPLICITLY names BOTH a source symbol and a target symbol (e.g., 'trace handle_create_user to save').
   - If the user asks about an abstract workflow (e.g. 'onboarding flow', 'auth flow') without mentioning exact code symbols, classify as 'exploratory'.
2. 'local_inspect': User asks about a specific class or function name.
3. 'comparison': User asks to compare two or more specific classes/modules.
4. 'blast_radius': User asks who calls or depends on a specific symbol.
5. 'exploratory': Open-ended questions about how a feature or workflow works where exact code symbols are unknown.
   - For 'exploratory' queries, leave 'initial_tasks' as an empty list []. The Orchestrator will plan the discovery searches.

CRITICAL GUARDRAIL - ZERO SYMBOL SPECULATION:
- NEVER guess or extrapolate symbol names based on query words (e.g., do NOT turn "billing" into "BillingService" or "export" into "DataExporter").
- If a class or function name is not typed verbatim in the user query, it DOES NOT EXIST.
- NEVER schedule 'trace_execution_flow' in initial_tasks unless the symbol names were written verbatim by the user.


OUTPUT FORMAT:
Return ONLY a single valid JSON object adhering strictly to this schema:
{
  "task_id": 1,
  "tool": "search_codebase",
  "objective": "Locate entry-point functions matching user query domain",
  "input_parameters": {"query": "<atomic_keyword_1> <atomic_keyword_2>", "top_k": 8}
}
"""


async def router_node(state: AgentState) -> Dict[str, Any]:
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )
    structured_router = llm.with_structured_output(
        RouterDecision,
        method="json_mode",
    )

    decision: RouterDecision = await structured_router.ainvoke(
        [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": state["query"]},
        ]
    )

    return {
        "router_decision": decision,
        "loop_count": 0,
    }
