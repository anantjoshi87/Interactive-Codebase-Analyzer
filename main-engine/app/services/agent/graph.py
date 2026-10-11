from functools import partial
from langgraph.graph import StateGraph, START, END

from app.services.agent.state import AgentState, QueryStrategy
from app.services.agent.router import router_node
from app.services.agent.orchestrator import orchestrator_node
from app.services.agent.dispatcher import tool_dispatcher_node
from app.services.agent.synthesizer import synthesizer_node


def route_after_router(state: AgentState) -> str:
    """
    If the router assigned a fixed recipe (initial_tasks present), dispatch them immediately.
    If the query is exploratory, route to the Orchestrator discovery loop.
    """
    decision = state.get("router_decision")
    if not decision:
        return "orchestrator"

    if decision.strategy != QueryStrategy.EXPLORATORY and decision.initial_tasks:
        return "tool_dispatcher"
    return "orchestrator"


def route_after_dispatcher(state: AgentState) -> str:
    """
    Decides whether to route to the Orchestrator for follow-up expansion or proceed to synthesis.
    """
    decision = state.get("router_decision")

    # Fixed recipes (comparison, blast_radius) evaluate once in orchestrator then move to synthesizer
    if decision and decision.strategy in {
        QueryStrategy.COMPARISON,
        QueryStrategy.BLAST_RADIUS,
    }:
        if state.get("loop_count", 0) >= 1:
            return "synthesizer"
        return "orchestrator"

    # Exploratory loop checks safety budget
    if state.get("loop_count", 0) >= 3:
        return "synthesizer"

    return "orchestrator"


def route_after_orchestrator(state: AgentState) -> str:
    """
    Exits to synthesis if the orchestrator is satisfied or the safety budget is reached.
    """
    decision = state.get("orchestrator_decision")
    if not decision:
        return "synthesizer"

    if decision.is_ready_to_synthesize or state.get("loop_count", 0) >= 3:
        return "synthesizer"

    return "tool_dispatcher"


def compile_agent_graph(tool_map: dict = None):
    """
    Compiles the agent graph. If tool_map is not passed,
    instantiates the repository and builds the default tool map.
    """
    if tool_map is None:
        from app.db.neo4j.neo4j_client import neo4j_client
        from app.db.neo4j.neo4j_repository import CodebaseRepository
        from app.services.agent.tools import build_tool_map

        repo = CodebaseRepository(neo4j_client)
        tool_map = build_tool_map(repo)

    builder = StateGraph(AgentState)

    builder.add_node("router", router_node)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node(
        "tool_dispatcher", partial(tool_dispatcher_node, tool_map=tool_map)
    )
    builder.add_node("synthesizer", synthesizer_node)

    # Entry edge
    builder.add_edge(START, "router")

    # Routing edges
    builder.add_conditional_edges(
        "router",
        route_after_router,
        {
            "tool_dispatcher": "tool_dispatcher",
            "orchestrator": "orchestrator",
        },
    )

    builder.add_conditional_edges(
        "tool_dispatcher",
        route_after_dispatcher,
        {
            "orchestrator": "orchestrator",
            "synthesizer": "synthesizer",
        },
    )

    builder.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "tool_dispatcher": "tool_dispatcher",
            "synthesizer": "synthesizer",
        },
    )

    builder.add_edge("synthesizer", END)

    return builder.compile()


# Module-level instance ready for test scripts and FastAPI routes
codebase_agent = compile_agent_graph()
