import asyncio
from rich.console import Console
from rich.table import Table
from app.services.agent.orchestrator import orchestrator_node

console = Console()


async def run_test(query: str):
    console.print(f"\n[bold yellow]User Query:[/bold yellow] [white]{query}[/white]\n")

    state = {"query": query, "plan": None, "worker_results": [], "final_answer": None}

    output = await orchestrator_node(state)
    plan = output["plan"]

    console.print(f"[bold cyan]Plan Reasoning:[/bold cyan] {plan.reasoning}\n")

    table = Table(
        title="Generated Subtasks for Workers",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Task ID", style="dim", width=8)
    table.add_column("Worker", style="green", width=18)
    table.add_column("Suggested Tool", style="cyan", width=18)
    table.add_column("Objective", style="white")
    table.add_column("Input Parameters", style="yellow")

    for task in plan.tasks:
        table.add_row(
            str(task.task_id),
            task.worker.value,
            str(task.tool_hint or "-"),
            task.objective,
            str(task.input_parameters),
        )

    console.print(table)


async def main():
    # Test query demonstrating both graph topology and semantic/context requirements
    complex_query = "How authentication works in this system."
    await run_test(complex_query)


if __name__ == "__main__":
    asyncio.run(main())
