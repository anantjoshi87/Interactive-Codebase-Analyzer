from typing import Any, Dict, List
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.agent.state import AgentState, OrchestratorDecision

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Systems Architect in an iterative codebase discovery loop.
Review the developer query and all facts collected so far, then plan the immediate next parallel batch of tasks.

TOOL CAPABILITIES:
- search_codebase(query: str, top_k: int = 8): Semantic search to find candidate symbols.
- get_symbol(symbol: str): Exact lookup for a class, method, or function.
- get_file(file_path: str): Retrieves all symbols in a file.
- get_node_context(node_ids: list[str]): Fetches metadata AND automatically reads raw source code from disk for known node IDs.
- read_code_snippet(file_path: str, start_line: int, end_line: int): Reads exact lines directly from a file.
- trace_execution_flow(source_symbol: str, candidate_target_symbols: list[str], max_depth: int = 6)
- find_callers(node_id: str)
- find_callees(node_id: str)
- get_neighbors(node_id: str, relationship_types: list[str], direction: str)
- web_search(query: str)

CRITICAL EXPANSION & EXECUTION RULES:
1. PHASE 1 (DISCOVERY):
- When no code units are known, use 'get_symbol' or 'search_codebase' to locate candidates.

2. PHASE 2 (FETCHING CODE IMPLEMENTATIONS):
- When symbols/classes are identified, you MUST inspect their actual implementation before synthesizing.
- PREFERRED: Call 'get_node_context(node_ids=[...])' with the discovered node IDs. It automatically slices the code from disk.
- ALTERNATIVE: Call 'read_code_snippet(file_path=..., start_line=..., end_line=...)' using coordinates from discovered units.

3. DEDUPLICATION (PREVENT SEARCH LOOPS):
- NEVER issue a search query or symbol lookup that has already been executed in earlier rounds.
- Do not repeat queries with minor variations (e.g. if 'auth' and 'jwt' returned empty, do not query 'token' or 'auth middleware').

4. TERMINATION & MISSING FEATURES:
- Set 'is_ready_to_synthesize=True' (with 'next_tasks': []) when:
  a) You have collected sufficient code implementations and call paths to answer the question, OR
  b) Initial discovery searches returned empty results, indicating the requested feature is NOT implemented in this codebase.
- Do NOT force additional searches if a concept does not exist. Let the Synthesizer report the feature's absence.

OUTPUT FORMAT:
- Return only one valid JSON object.
- The JSON object must contain: reasoning, is_ready_to_synthesize, and next_tasks.
- Each next_tasks item must contain: task_id, tool, objective, and input_parameters.
- task_id must be a JSON number (for example 1 or 2), never a string such as "task_1".
"""


def _format_context_for_planner(gathered_context: List[Dict[str, Any]]) -> str:
    if not gathered_context:
        return "No prior facts collected. This is Round 1 (Discovery Phase)."

    formatted_lines = []
    executed_queries = []

    for item in gathered_context:
        tool_name = item.get("tool")
        data = item.get("data")
        task_id = item.get("task_id")

        if tool_name in {"search_codebase", "get_symbol"}:
            executed_queries.append(f"{tool_name}: {item.get('summary')}")

        if not data:
            formatted_lines.append(
                f"- Task {task_id} ({tool_name}): Returned 0 results."
            )
            continue

        if isinstance(data, list):
            formatted_lines.append(f"\n[Task {task_id} Results from {tool_name}]:")
            for node in data:
                if isinstance(node, dict) and "id" in node:
                    formatted_lines.append(
                        f"  * Node ID: '{node.get('id')}' | Symbol: '{node.get('qualified_name')}' | File: '{node.get('file_path')}' (Lines {node.get('start_line')}-{node.get('end_line')})"
                    )
                else:
                    formatted_lines.append(f"  * {str(node)[:150]}")

    history_block = "Executed Queries History:\n" + "\n".join(
        f"- {q}" for q in executed_queries
    )
    return history_block + "\n\nDiscovered Code Units:\n" + "\n".join(formatted_lines)


async def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,
    )
    structured_planner = llm.with_structured_output(
        OrchestratorDecision,
        method="json_mode",
    )

    history_text = _format_context_for_planner(state.get("gathered_context", []))

    user_prompt = f"""Developer Query: {state['query']}

Current State (Round {state.get('loop_count', 0) + 1}):
{history_text}
"""

    decision: OrchestratorDecision = await structured_planner.ainvoke(
        [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )

    return {
        "orchestrator_decision": decision,
        "loop_count": state.get("loop_count", 0) + 1,
    }
