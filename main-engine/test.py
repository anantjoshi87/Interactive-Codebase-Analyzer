import json
from app.services.ingestion.parser import RepoFetcher, RepoParser
from rich import print
from rich.panel import Panel
from rich.syntax import Syntax

# Initialize parser
parser = RepoParser()

# Test repository (or swap with any repo containing both JS/JSX and Python)
repo_url = "https://github.com/anantjoshi87/smart-study-planner-python.git"

with RepoFetcher.clone_to_temp(repo_url) as repo_path:
    extracted_units = parser.parse_repository(repo_path)
    
    # Helper function to convert dataclasses / Pydantic objects to dicts
    def to_dict(unit):
        if hasattr(unit, "model_dump"):
            return unit.model_dump()
        elif hasattr(unit, "__dict__"):
            return unit.__dict__
        return unit if isinstance(unit, dict) else str(unit)

    # 1. Find the first Python unit
    py_unit = next(
        (unit for unit in extracted_units if str(to_dict(unit).get("file_path", "")).endswith(".py")), 
        None
    )

    # 2. Find the first JSX/JS unit
    jsx_unit = next(
        (unit for unit in extracted_units if str(to_dict(unit).get("file_path", "")).endswith((".jsx", ".js", ".tsx", ".ts"))), 
        None
    )

    # --- DISPLAY PYTHON UNIT ---
    print("\n[bold cyan]=================== 🐍 PYTHON EXTRACTED UNIT ===================[/bold cyan]\n")
    if py_unit:
        py_data = to_dict(py_unit)
        print("[bold yellow]Metadata & Attributes:[/bold yellow]")
        print({k: v for k, v in py_data.items() if k != "code_content" and k != "content"})
        
        code = py_data.get("code_content") or py_data.get("content") or "# No code content property found"
        print("\n[bold yellow]Retrieved Code Snippet:[/bold yellow]")
        print(Panel(Syntax(code, "python", theme="monokai", line_numbers=True), title=str(py_data.get("file_path"))))
    else:
        print("[red]No Python (.py) files found in this repository.[/red]")

    # --- DISPLAY JSX UNIT ---
    print("\n[bold cyan]=================== ⚛️ JSX / JS EXTRACTED UNIT ===================[/bold cyan]\n")
    if jsx_unit:
        jsx_data = to_dict(jsx_unit)
        print("[bold yellow]Metadata & Attributes:[/bold yellow]")
        print({k: v for k, v in jsx_data.items() if k != "code_content" and k != "content"})
        
        code = jsx_data.get("code_content") or jsx_data.get("content") or "// No code content property found"
        print("\n[bold yellow]Retrieved Code Snippet:[/bold yellow]")
        print(Panel(Syntax(code, "jsx", theme="monokai", line_numbers=True), title=str(jsx_data.get("file_path"))))
    else:
        print("[yellow]No JSX/JS files found in this specific repo. (Tip: Try testing on a full-stack repo containing React frontend files).[/yellow]")