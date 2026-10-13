import operator
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator
from typing_extensions import TypedDict


class QueryStrategy(str, Enum):
    COMPARISON = "comparison"
    BLAST_RADIUS = "blast_radius"
    FLOW_TRACE = "flow_trace"
    LOCAL_INSPECT = "local_inspect"
    EXPLORATORY = "exploratory"


class SubTask(BaseModel):
    task_id: int = 1
    tool: str
    objective: str = ""
    input_parameters: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_subtask(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        # Shortcut Case: LLM output {"search_codebase": {"query": "...", "top_k": 5}}
        standard_keys = {"task_id", "tool", "objective", "input_parameters"}
        if not any(k in data for k in standard_keys) and len(data) == 1:
            tool_name, params = next(iter(data.items()))
            return {
                "task_id": 1,
                "tool": tool_name,
                "objective": f"Execute {tool_name}",
                "input_parameters": (
                    params if isinstance(params, dict) else {"query": str(params)}
                ),
            }

        # Flat Case: LLM output {"tool": "search_codebase", "query": "..."} without "input_parameters"
        if "tool" in data and "input_parameters" not in data:
            tool = data["tool"]
            params = {k: v for k, v in data.items() if k not in standard_keys}
            return {
                "task_id": data.get("task_id", 1),
                "tool": tool,
                "objective": data.get("objective", f"Execute {tool}"),
                "input_parameters": params or data.get("parameters", {}),
            }

        # Missing optional fields: Provide safe defaults
        if "task_id" not in data:
            data["task_id"] = 1
        if "objective" not in data:
            data["objective"] = f"Execute {data.get('tool', 'tool')}"
        if "input_parameters" not in data:
            data["input_parameters"] = {}

        return data


class RouterDecision(BaseModel):
    strategy: QueryStrategy = Field(
        default=QueryStrategy.EXPLORATORY,
        description="The routing recipe to follow for this query.",
    )
    reasoning: str = Field(
        default="No reasoning provided.",
        description="Brief explanation of why this strategy was chosen.",
    )
    target_entities: List[str] = Field(
        default_factory=list,
        description="Named classes, functions, or files mentioned verbatim in the query.",
    )
    initial_tasks: List[SubTask] = Field(
        default_factory=list,
        description="Pre-allocated tasks for deterministic recipes (empty for exploratory).",
    )


class OrchestratorDecision(BaseModel):
    reasoning: str = Field(
        default="No reasoning provided.",
        description="Architectural evaluation of facts.",
    )
    is_ready_to_synthesize: bool = Field(
        default=False,
        description="True if collected facts are sufficient to write the final answer.",
    )
    next_tasks: List[SubTask] = Field(
        default_factory=list,
        description="Parallel batch of subtasks to execute in the next round.",
    )


class AgentState(TypedDict):
    query: str
    router_decision: Optional[RouterDecision]
    orchestrator_decision: Optional[OrchestratorDecision]
    # operator.add ensures parallel and multi-turn outputs accumulate monotonically
    gathered_context: Annotated[List[Dict[str, Any]], operator.add]
    loop_count: int
    final_answer: Optional[str]


# from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

# from langchain_core.messages import BaseMessage
# from langgraph.graph.message import add_messages


# class Evidence(TypedDict, total=False):
#     """
#     A piece of evidence collected from the repository.

#     This is intentionally structured so the final answer can later
#     cite where a conclusion came from.
#     """

#     node_id: str
#     qualified_name: str
#     file_path: str
#     symbol_kind: str
#     summary: str

#     source_code: Optional[str]

#     relationship: Optional[str]
#     related_node_id: Optional[str]
#     related_qualified_name: Optional[str]

#     relevance_score: Optional[float]


# class AgentState(TypedDict):
#     # ---------------------------------------------------------
#     # Conversation / tool history
#     # ---------------------------------------------------------

#     messages: Annotated[Sequence[BaseMessage], add_messages]

#     # ---------------------------------------------------------
#     # Original user question
#     # ---------------------------------------------------------

#     query: str

#     # ---------------------------------------------------------
#     # Current investigation frontier
#     #
#     # Nodes the agent currently considers worth exploring.
#     # ---------------------------------------------------------

#     active_node_ids: List[str]

#     # ---------------------------------------------------------
#     # Nodes already investigated
#     #
#     # Prevents repeatedly exploring the same nodes.
#     # ---------------------------------------------------------

#     visited_node_ids: List[str]

#     # ---------------------------------------------------------
#     # Grounded evidence collected during investigation
#     # ---------------------------------------------------------

#     gathered_context: List[Evidence]

#     # ---------------------------------------------------------
#     # Things the agent believes it still needs to answer
#     # ---------------------------------------------------------

#     missing_evidence: List[str]

#     # ---------------------------------------------------------
#     # Investigation budget
#     # ---------------------------------------------------------

#     tool_calls: int

#     # ---------------------------------------------------------
#     # Final response
#     # ---------------------------------------------------------

#     final_answer: Optional[str]
