"""Manage intermediate steps for a plan."""
from datetime import date
from rich.prompt import Prompt, Confirm
from db.database import get_db
from utils.display import console, section, step_table


def _pick_plan() -> dict | None:
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, a.title, p.scheduled_date
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NULL
            ORDER BY p.scheduled_date ASC"""
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No active plans found. Create a plan first.[/yellow]")
        return None

    console.print("\n[bold]Your active plans:[/bold]")
    for r in rows:
        date_str = r["scheduled_date"] or "TBD"
        console.print(f"  [cyan]{r['id']}[/cyan]  {r['title']}  [dim](scheduled: {date_str})[/dim]")

    valid_ids = [str(r["id"]) for r in rows]
    chosen_id = Prompt.ask("\nEnter plan # to manage steps for", choices=valid_ids)
    return next(r for r in rows if str(r["id"]) == chosen_id)


def manage_steps() -> None:
    section("Manage Plan Steps", "yellow")

    plan = _pick_plan()
    if not plan:
        return

    plan_id = plan["id"]

    while True:
        _show_steps(plan_id, plan["title"])

        console.print(
            "\n[cyan]1[/cyan] Mark a step done  "
            "[cyan]2[/cyan] Add a step  "
            "[cyan]3[/cyan] Delete a step  "
            "[cyan]4[/cyan] Back"
        )
        action = Prompt.ask("Action", choices=["1", "2", "3", "4"], default="4")

        if action == "1":
            _mark_step_done(plan_id)
        elif action == "2":
            _add_step(plan_id)
        elif action == "3":
            _delete_step(plan_id)
        elif action == "4":
            break


def _show_steps(plan_id: int, title: str) -> None:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, description, due_date, is_done FROM steps WHERE plan_id = ? ORDER BY order_index, id",
        (plan_id,),
    ).fetchall()
    conn.close()

    console.print(f"\n[bold]Steps for:[/bold] {title}")
    if not rows:
        console.print("  [dim]No steps yet.[/dim]")
        return
    console.print(step_table(rows))

    done = sum(1 for r in rows if r["is_done"])
    console.print(f"[dim]{done}/{len(rows)} steps completed.[/dim]")


def _mark_step_done(plan_id: int) -> None:
    conn = get_db()
    pending = conn.execute(
        "SELECT id, description FROM steps WHERE plan_id = ? AND is_done = 0 ORDER BY order_index, id",
        (plan_id,),
    ).fetchall()
    conn.close()

    if not pending:
        console.print("[yellow]All steps are already done![/yellow]")
        return

    for r in pending:
        console.print(f"  [cyan]{r['id']}[/cyan]  {r['description']}")

    valid_ids = [str(r["id"]) for r in pending]
    step_id = Prompt.ask("Step # to mark done", choices=valid_ids)

    conn = get_db()
    with conn:
        conn.execute("UPDATE steps SET is_done = 1 WHERE id = ?", (int(step_id),))
    conn.close()
    console.print("[green]✓ Step marked as done.[/green]")


def _add_step(plan_id: int) -> None:
    desc = Prompt.ask("Step description").strip()
    if not desc:
        console.print("[red]Description cannot be empty.[/red]")
        return
    due = Prompt.ask("Due date [dim](YYYY-MM-DD or blank)[/dim]", default="").strip()
    if due:
        try:
            date.fromisoformat(due)
        except ValueError:
            console.print("[red]Invalid date — saved without due date.[/red]")
            due = ""

    conn = get_db()
    with conn:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(order_index), 0) FROM steps WHERE plan_id = ?", (plan_id,)
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO steps (plan_id, description, due_date, order_index) VALUES (?, ?, ?, ?)",
            (plan_id, desc, due or None, max_order + 1),
        )
    conn.close()
    console.print("[green]✓ Step added.[/green]")


def _delete_step(plan_id: int) -> None:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, description FROM steps WHERE plan_id = ? ORDER BY order_index, id",
        (plan_id,),
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No steps to delete.[/yellow]")
        return

    for r in rows:
        console.print(f"  [cyan]{r['id']}[/cyan]  {r['description']}")

    valid_ids = [str(r["id"]) for r in rows]
    step_id = Prompt.ask("Step # to delete", choices=valid_ids)

    if Confirm.ask(f"Delete step {step_id}?", default=False):
        conn = get_db()
        with conn:
            conn.execute("DELETE FROM steps WHERE id = ?", (int(step_id),))
        conn.close()
        console.print("[green]✓ Step deleted.[/green]")
