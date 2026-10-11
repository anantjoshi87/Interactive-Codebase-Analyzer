import operator
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class QueryStrategy(str, Enum):
    COMPARISON = "comparison"  # Comparing two classes, methods, or modules
    BLAST_RADIUS = "blast_radius"  # Upstream caller analysis / impact checking
    FLOW_TRACE = "flow_trace"  # Tracing execution paths from A to B
    LOCAL_INSPECT = "local_inspect"  # What does a specific symbol do
    EXPLORATORY = "exploratory"  # Broad questions with unknown symbols (auth, cache)


class SubTask(BaseModel):
    task_id: int = Field(description="Unique incremental integer ID")
    tool: str = Field(description="Tool name to execute from TOOL_REGISTRY")
    objective: str = Field(description="Purpose of this task")
    input_parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strictly literal input parameters matching tool signatures. No placeholders.",
    )


class RouterDecision(BaseModel):
    strategy: QueryStrategy = Field(description="Classified execution strategy")
    target_entities: List[str] = Field(
        default_factory=list,
        description="Explicit symbols, files, or concepts extracted from the prompt",
    )
    reasoning: str = Field(description="Why this strategy was selected")
    initial_tasks: List[SubTask] = Field(
        default_factory=list,
        description="Pre-computed recipe tasks if strategy is not exploratory",
    )


class OrchestratorDecision(BaseModel):
    reasoning: str
    is_ready_to_synthesize: bool = Field(
        description="True if collected context is sufficient to answer the query"
    )
    next_tasks: List[SubTask] = Field(
        default_factory=list,
        description="Next batch of parallel tasks (empty if ready to synthesize)",
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
