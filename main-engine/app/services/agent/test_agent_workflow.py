# python -m app.services.agent.test_agent_workflow

import asyncio
from rich.console import Console
from rich.panel import Panel
from app.services.agent.graph import codebase_agent

console = Console()


async def run_query(query: str):
    console.print(f"\n[bold yellow]>>> Query:[/bold yellow] [white]{query}[/white]\n")

    initial_state = {
        "query": query,
        "router_decision": None,
        "orchestrator_decision": None,
        "gathered_context": [],
        "loop_count": 0,
        "final_answer": None,
    }

    async for event in codebase_agent.astream(initial_state, stream_mode="updates"):
        for node_name, updates in event.items():
            console.print(
                f"[bold cyan]Completed Node:[/bold cyan] [green]{node_name}[/green]"
            )

            if node_name == "router":
                d = updates["router_decision"]
                console.print(f"  Strategy: [yellow]{d.strategy.value}[/yellow]")
                console.print(f"  Initial Tasks: {len(d.initial_tasks)}")

            elif node_name == "tool_dispatcher":
                gathered = updates.get("gathered_context", [])
                console.print(f"  Parallel Tasks Executed: {len(gathered)}")
                for res in gathered:
                    status = (
                        "[green]✓[/green]" if res.get("success") else "[red]✗[/red]"
                    )
                    console.print(
                        f"    {status} {res.get('tool')}: {res.get('summary')[:90]}..."
                    )

            elif node_name == "orchestrator":
                d = updates["orchestrator_decision"]
                console.print(f"  Ready to Synthesize: {d.is_ready_to_synthesize}")
                console.print(f"  Next Planned Tasks: {len(d.next_tasks)}")

            elif node_name == "synthesizer":
                # ✅ After: Pass as separate arguments or print the Panel directly
                console.print()
                console.print(
                    Panel(
                        updates["final_answer"],
                        title="Synthesizer Output",
                        border_style="magenta",
                    )
                )


async def main():
    # 1. Test Deterministic Comparison Recipe
    await run_query(
        "Explain me this repository's codebase architecture."
    )


if __name__ == "__main__":
    asyncio.run(main())
