from typing import Any, Dict, List
from langchain_groq import ChatGroq
from app.core.config import settings
from app.services.agent.state import AgentState, OrchestratorDecision

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Lead Systems Architect in an iterative codebase discovery loop.
Review the developer query and all facts collected so far, then plan the immediate next parallel batch of tasks.

TOOL CAPABILITIES:
- search_codebase(query: str, top_k: int = 8): Semantic + fulltext hybrid search.
- get_symbol(symbol: str): Exact lookup for a class, method, or function.
- get_file(file_path: str): Retrieves all symbols in a file.
- get_node_context(node_ids: list[str]): Fetches metadata AND raw source code from disk.
- read_code_snippet(file_path: str, start_line: int, end_line: int): Reads exact lines from disk.
- trace_execution_flow(source_symbol: str, candidate_target_symbols: list[str], max_depth: int = 6)
- find_callers(node_id: str)
- find_callees(node_id: str)
- get_neighbors(node_id: str, relationship_types: list[str], direction: str)
- web_search(query: str)

CRITICAL SEARCH & REASONING RULES:
1. DE-JARGON BUSINESS CONCEPTS (ROUND 1):
   Developers ask in high-level business terms, but codebases use low-level technical verbs and entities.
   Always translate user intent into 2-3 atomic technical search keywords across different domains:
   - "onboarding / signup flow"  -> search 'register' or 'create_user'
   - "checkout / payment flow"   -> search 'charge', 'invoice', or 'stripe'
   - "scheduled / cron tasks"    -> search 'schedule', 'periodic', or 'worker'
   - "data export to spreadsheet"-> search 'csv', 'download', or 'generate_report'
   - "alerting / notifications"  -> search 'notify', 'dispatch', or 'email'


2. PHASE 2 (VERIFICATION & TRACING):
   - Once candidate symbols are found (e.g. 'UserService.register_user'), use 'get_node_context' or 'trace_execution_flow' using ONLY the discovered IDs.

3. DEDUPLICATION:
   - NEVER repeat queries or near-duplicates that have already been searched.

4. TERMINATION:
   - Set 'is_ready_to_synthesize=True' (with 'next_tasks': []) when:
     a) You have collected the code snippets and call paths to answer the question, OR
     b) Broad searches for atomic terms returned empty, proving the feature is absent.

OUTPUT FORMAT:
You must return ONLY a single valid JSON object adhering strictly to the schema below:
{
  "reasoning": "Explanation of current state and planned next actions",
  "is_ready_to_synthesize": false,
  "next_tasks": [
    {
      "task_id": 1,
      "tool": "search_codebase",
      "objective": "Find user registration implementation",
      "input_parameters": {"query": "register user", "top_k": 5}
    }
  ]
}
"""


def _format_context_for_planner(
    gathered_context: List[Dict[str, Any]],
) -> str:
    if not gathered_context:
        return "No prior facts collected. This is Round 1 (Discovery Phase)."

    formatted_lines = ["Discovered Code Units and Coordinates:"]
    for item in gathered_context:
        tool_name = item.get("tool")
        data = item.get("data")
        task_id = item.get("task_id")

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
        OrchestratorDecision, method="json_mode"
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
