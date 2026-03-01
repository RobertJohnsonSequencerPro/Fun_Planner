"""Rich-based display helpers shared across modules."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

console = Console()


def section(title: str, color: str = "cyan") -> None:
    console.print(Panel(f"[bold {color}]{title}[/bold {color}]", border_style=color))


def activity_table(rows, *, show_status: bool = True) -> Table:
    """Return a Rich Table populated with activity rows."""
    t = Table(box=box.ROUNDED, header_style="bold cyan", show_lines=False)
    t.add_column("#", style="dim", width=4)
    t.add_column("Title", min_width=20)
    t.add_column("Category", width=14)
    t.add_column("Energy", width=8)
    t.add_column("Cost", width=10)
    if show_status:
        t.add_column("Status", width=9)
    t.add_column("Tags", min_width=12)

    status_colors = {
        "idea": "yellow",
        "planned": "blue",
        "done": "green",
        "skipped": "dim",
    }

    for r in rows:
        status_cell = f"[{status_colors.get(r['status'], 'white')}]{r['status']}[/]" if show_status else ""
        cols = [
            str(r["id"]),
            r["title"],
            r["category"],
            r["energy_level"],
            r["cost_estimate"],
        ]
        if show_status:
            cols.append(status_cell)
        cols.append(r["tags"] or "")
        t.add_row(*cols)
    return t


def plan_table(rows) -> Table:
    """Return a Rich Table populated with plan rows (joined with activity title)."""
    t = Table(box=box.ROUNDED, header_style="bold magenta", show_lines=False)
    t.add_column("#", style="dim", width=4)
    t.add_column("Activity", min_width=22)
    t.add_column("Date", width=12)
    t.add_column("Steps done", width=12)
    t.add_column("Status", width=10)

    for r in rows:
        done = r["steps_done"] or 0
        total = r["steps_total"] or 0
        progress = f"{done}/{total}" if total else "—"
        status = "[green]done[/green]" if r["completed_at"] else "[blue]upcoming[/blue]"
        t.add_row(str(r["id"]), r["title"], r["scheduled_date"] or "TBD", progress, status)
    return t


def step_table(rows) -> Table:
    t = Table(box=box.SIMPLE, header_style="bold", show_lines=False)
    t.add_column("#", style="dim", width=4)
    t.add_column("", width=3)   # checkbox
    t.add_column("Step", min_width=30)
    t.add_column("Due", width=12)

    for r in rows:
        check = "[green]✓[/green]" if r["is_done"] else "[ ]"
        t.add_row(str(r["id"]), check, r["description"], r["due_date"] or "—")
    return t
