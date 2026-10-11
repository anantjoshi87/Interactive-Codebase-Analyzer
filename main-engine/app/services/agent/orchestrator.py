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

CRITICAL EXPANSION & CODE INSPECTION RULES:
1. PHASE 1 (DISCOVERY):
   - When no code units are known, use 'get_symbol' or 'search_codebase' to locate candidates.
2. PHASE 2 (FETCHING CODE IMPLEMENTATIONS):
   - When symbols/classes are identified, you MUST inspect their actual implementation before synthesizing.
   - PREFERRED: Call 'get_node_context(node_ids=[...])' with the discovered node IDs. It automatically slices the code from disk.
   - ALTERNATIVE: Call 'read_code_snippet(file_path=..., start_line=..., end_line=...)' using the coordinates shown in the discovered units list.
3. TERMINATION:
   - Only set 'is_ready_to_synthesize=True' when you have actual code implementations, method bodies, or call paths to answer the question thoroughly.
"""


def _format_context_for_planner(gathered_context: List[Dict[str, Any]]) -> str:
    """
    Extracts essential navigation coordinates (ID, file, lines)
    from previous tool outputs without token-heavy embeddings or truncation.
    """
    if not gathered_context:
        return "No prior facts collected. This is Round 1 (Discovery Phase)."

    formatted_lines = ["Discovered Code Units and Coordinates:"]

    for item in gathered_context:
        tool_name = item.get("tool")
        data = item.get("data")
        task_id = item.get("task_id")

        if not data:
            formatted_lines.append(f"- Task {task_id} ({tool_name}): No results found.")
            continue

        # If data is a list of Neo4j node dicts (from get_symbol, search_codebase, get_file)
        if isinstance(data, list):
            formatted_lines.append(f"\n[Task {task_id} Results from {tool_name}]:")
            for node in data:
                if isinstance(node, dict) and "id" in node:
                    node_id = node.get("id")
                    file_path = node.get("file_path")
                    st = node.get("start_line")
                    end = node.get("end_line")
                    name = node.get("qualified_name") or node.get("symbol_name")
                    formatted_lines.append(
                        f"  * Node ID: '{node_id}' | Symbol: '{name}' | File: '{file_path}' (Lines {st}-{end})"
                    )
                else:
                    formatted_lines.append(f"  * {str(node)[:180]}")
        else:
            formatted_lines.append(f"- Task {task_id} ({tool_name}): {str(data)[:250]}")

    return "\n".join(formatted_lines)


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
