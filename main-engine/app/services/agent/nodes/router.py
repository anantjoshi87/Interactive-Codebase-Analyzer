from typing import Any, Dict
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.agent.state import AgentState, QueryStrategy, RouterDecision, SubTask

ROUTER_SYSTEM_PROMPT = """You are the Senior Routing Architect for an Agentic Codebase Intelligence Engine.
Analyze the user query and classify it into an execution strategy.

Strategy Options:
1. 'comparison': User asks to compare two or more classes, methods, or modules.
   -> Recipe: Parallel get_symbol for both targets and their key methods.
2. 'blast_radius': User asks who calls a function, what depends on it, or what breaks.
   -> Recipe: get_symbol for target, then find_callers.
3. 'flow_trace': User asks how component A reaches or calls component B.
   -> Recipe: search_codebase for target sinks, then trace_execution_flow.
4. 'local_inspect': User asks what a single function or class does internally.
   -> Recipe: get_symbol for target, then get_node_context.
5. 'exploratory': Broad, open-ended question where specific symbol names are unknown (e.g., 'how does auth work?').
   -> Recipe: Leave initial_tasks EMPTY. The Orchestrator discovery loop handles this.

STRICT TOOL PARAMETER SIGNATURES:
- get_symbol: MUST use key 'symbol' (e.g. {"symbol": "UserRepository"}). NEVER use 'symbol_name'.
- search_codebase: MUST use key 'query' (e.g. {"query": "auth tokens", "top_k": 5}).
- get_file: MUST use key 'file_path' (e.g. {"file_path": "app/db/user.py"}).
- find_callers: MUST use key 'node_id' (e.g. {"node_id": "app/db/user.py::UserRepository"}).
- find_callees: MUST use key 'node_id'.
- trace_execution_flow: MUST use keys 'source_symbol' and 'candidate_target_symbols'.
- read_code_snippet: MUST use keys 'file_path', 'start_line', 'end_line'.
- web_search: MUST use key 'query'.

CRITICAL RULES:
- If strategy is NOT 'exploratory', populate 'initial_tasks' with concrete, immediately executable SubTask items.
- All input_parameters must strictly adhere to the exact parameter names above.

OUTPUT FORMAT:
- Return only one valid JSON object.
- The JSON object must contain: strategy, target_entities, reasoning, and initial_tasks.
- Each initial_tasks item must contain: task_id, tool, objective, and input_parameters.
- task_id must be a JSON number (for example 1 or 2), never a string such as "task_1".
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
