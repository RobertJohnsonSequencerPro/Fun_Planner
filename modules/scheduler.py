"""Convert an idea into a scheduled plan and view upcoming plans."""
from datetime import date
from rich.prompt import Prompt, Confirm
from db.database import get_db
from db.models import DEFAULT_STEPS
from utils.display import console, section, plan_table


def _pick_idea() -> dict | None:
    """Let the user choose from their unplanned ideas. Returns the chosen row or None."""
    conn = get_db()
    rows = conn.execute(
        """SELECT a.id, a.title, a.category, a.energy_level, a.cost_estimate
             FROM activities a
            WHERE a.status = 'idea'
            ORDER BY a.created_at DESC"""
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No unplanned ideas found. Add some ideas first![/yellow]")
        return None

    console.print("\n[bold]Your unplanned ideas:[/bold]")
    for r in rows:
        console.print(f"  [cyan]{r['id']}[/cyan]  {r['title']}  [dim]({r['category']} · {r['energy_level']} energy · {r['cost_estimate']})[/dim]")

    valid_ids = [str(r["id"]) for r in rows]
    chosen_id = Prompt.ask("\nEnter idea # to plan", choices=valid_ids)
    return next(r for r in rows if str(r["id"]) == chosen_id)


def plan_activity() -> None:
    section("Plan an Activity", "blue")

    idea = _pick_idea()
    if not idea:
        return

    console.print(f"\nPlanning: [bold]{idea['title']}[/bold]")

    # Scheduled date
    today = date.today().isoformat()
    scheduled_date = Prompt.ask("Scheduled date [dim](YYYY-MM-DD, or leave blank for TBD)[/dim]", default="").strip()
    if scheduled_date and not _valid_date(scheduled_date):
        console.print("[red]Invalid date format — saving as TBD.[/red]")
        scheduled_date = ""

    plan_notes = Prompt.ask("Any notes for this plan? [dim](optional)[/dim]", default="").strip()

    conn = get_db()
    with conn:
        cur = conn.execute(
            "INSERT INTO plans (activity_id, scheduled_date, notes) VALUES (?, ?, ?)",
            (idea["id"], scheduled_date or None, plan_notes),
        )
        plan_id = cur.lastrowid
        # Update activity status → planned
        conn.execute("UPDATE activities SET status = 'planned' WHERE id = ?", (idea["id"],))
    conn.close()

    console.print(f"\n[green]✓ Plan created (plan id={plan_id})[/green]")

    # Offer to add steps immediately
    if Confirm.ask("\nWould you like to add steps now?", default=True):
        _add_steps_for_plan(plan_id, idea["category"])


def _add_steps_for_plan(plan_id: int, category: str) -> None:
    suggestions = DEFAULT_STEPS.get(category, DEFAULT_STEPS["other"])

    if Confirm.ask(f"\nLoad {len(suggestions)} suggested steps for '{category}' activities?", default=True):
        conn = get_db()
        with conn:
            for i, desc in enumerate(suggestions, start=1):
                conn.execute(
                    "INSERT INTO steps (plan_id, description, order_index) VALUES (?, ?, ?)",
                    (plan_id, desc, i),
                )
        conn.close()
        console.print(f"[green]✓ {len(suggestions)} suggested steps added.[/green]")

    console.print("\nAdd custom steps (press Enter with no text to stop):")
    order = len(suggestions) + 1 if Confirm.ask("Were suggested steps added above?", default=True) else 1
    conn = get_db()
    with conn:
        while True:
            desc = Prompt.ask(f"  Step {order}", default="").strip()
            if not desc:
                break
            due = Prompt.ask("    Due date [dim](YYYY-MM-DD or blank)[/dim]", default="").strip()
            if due and not _valid_date(due):
                due = ""
            conn.execute(
                "INSERT INTO steps (plan_id, description, due_date, order_index) VALUES (?, ?, ?, ?)",
                (plan_id, desc, due or None, order),
            )
            order += 1
    conn.close()

    if order > 1:
        console.print("[green]✓ Custom steps saved.[/green]")


def view_upcoming() -> None:
    section("Upcoming Plans", "blue")

    today = date.today().isoformat()
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, a.title, p.scheduled_date, p.completed_at,
                  SUM(s.is_done)    AS steps_done,
                  COUNT(s.id)       AS steps_total
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
             LEFT JOIN steps s ON s.plan_id = p.id
            WHERE p.completed_at IS NULL
            GROUP BY p.id
            ORDER BY CASE WHEN p.scheduled_date IS NULL THEN 1 ELSE 0 END,
                     p.scheduled_date ASC"""
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]No upcoming plans yet. Use 'Plan something' to get started![/yellow]")
        return

    console.print(plan_table(rows))
    console.print(f"[dim]{len(rows)} upcoming plan(s).[/dim]")


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False
