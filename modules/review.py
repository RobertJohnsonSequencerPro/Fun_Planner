"""Review past activities — mark them done, add ratings and reflections."""
from datetime import datetime, date
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich import box
from db.database import get_db
from utils.display import console, section


def review_past() -> None:
    section("Review Past Activities", "green")

    today = date.today().isoformat()
    conn = get_db()

    # Plans that are due (scheduled date has passed) but not yet marked complete
    overdue = conn.execute(
        """SELECT p.id, a.title, p.scheduled_date, a.category,
                  SUM(s.is_done) AS steps_done, COUNT(s.id) AS steps_total
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
             LEFT JOIN steps s ON s.plan_id = p.id
            WHERE p.completed_at IS NULL
              AND (p.scheduled_date <= ? OR p.scheduled_date IS NULL)
            GROUP BY p.id
            ORDER BY p.scheduled_date ASC""",
        (today,),
    ).fetchall()
    conn.close()

    if not overdue:
        console.print("[dim]Nothing to review right now — all plans are upcoming or already done.[/dim]")
        _show_history()
        return

    # Show them in a table
    t = Table(box=box.ROUNDED, header_style="bold green")
    t.add_column("#", style="dim", width=4)
    t.add_column("Activity", min_width=22)
    t.add_column("Scheduled", width=12)
    t.add_column("Steps", width=10)
    for r in overdue:
        done = r["steps_done"] or 0
        total = r["steps_total"] or 0
        t.add_row(str(r["id"]), r["title"], r["scheduled_date"] or "TBD", f"{done}/{total}")
    console.print(t)

    valid_ids = [str(r["id"]) for r in overdue]
    plan_id_str = Prompt.ask("Enter plan # to review (or 'q' to skip)", default="q")
    if plan_id_str not in valid_ids:
        return

    plan = next(r for r in overdue if str(r["id"]) == plan_id_str)

    console.print(f"\nReviewing: [bold]{plan['title']}[/bold]")

    did_it = Confirm.ask("Did you do this activity?", default=True)
    if not did_it:
        if Confirm.ask("Mark it as skipped?", default=False):
            conn = get_db()
            with conn:
                conn.execute("UPDATE activities SET status = 'skipped' WHERE id = (SELECT activity_id FROM plans WHERE id = ?)", (int(plan_id_str),))
                conn.execute("UPDATE plans SET completed_at = ? WHERE id = ?", (datetime.now().isoformat(), int(plan_id_str)))
            conn.close()
            console.print("[dim]Marked as skipped.[/dim]")
        return

    # Rating
    console.print("\nHow was it? [cyan]1[/cyan]=poor  [cyan]2[/cyan]=ok  [cyan]3[/cyan]=good  [cyan]4[/cyan]=great  [cyan]5[/cyan]=amazing")
    rating = int(Prompt.ask("Rating", choices=["1", "2", "3", "4", "5"], default="4"))

    reflection = Prompt.ask("Any notes or reflections? [dim](optional)[/dim]", default="").strip()

    conn = get_db()
    with conn:
        conn.execute(
            """UPDATE plans
                  SET completed_at = ?, rating = ?, reflection = ?
                WHERE id = ?""",
            (datetime.now().isoformat(), rating, reflection, int(plan_id_str)),
        )
        conn.execute(
            "UPDATE activities SET status = 'done' WHERE id = (SELECT activity_id FROM plans WHERE id = ?)",
            (int(plan_id_str),),
        )
    conn.close()

    stars = "★" * rating + "☆" * (5 - rating)
    console.print(f"\n[bold green]✓ Marked as done![/bold green]  {stars}")


def _show_history() -> None:
    if not Confirm.ask("\nView activity history?", default=False):
        return

    conn = get_db()
    rows = conn.execute(
        """SELECT a.title, p.scheduled_date, p.completed_at, p.rating, p.reflection
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NOT NULL
            ORDER BY p.completed_at DESC
            LIMIT 20"""
    ).fetchall()
    conn.close()

    if not rows:
        console.print("[dim]No completed activities yet.[/dim]")
        return

    t = Table(box=box.SIMPLE, header_style="bold")
    t.add_column("Activity", min_width=22)
    t.add_column("Done on", width=12)
    t.add_column("Rating", width=8)
    t.add_column("Reflection", min_width=24)

    for r in rows:
        stars = ("★" * r["rating"] + "☆" * (5 - r["rating"])) if r["rating"] else "—"
        done_date = r["completed_at"][:10] if r["completed_at"] else "—"
        t.add_row(r["title"], done_date, stars, r["reflection"] or "")

    console.print(t)
