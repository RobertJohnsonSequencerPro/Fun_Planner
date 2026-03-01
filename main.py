"""Fun Activity Planner — entry point."""
from datetime import date
from rich.prompt import Prompt
from rich.panel import Panel
from db.database import init_db, get_db
from utils.display import console
from modules import capture, browser, scheduler, steps, review


def _show_nudges() -> None:
    """Surface any plans coming up in the next 7 days."""
    today = date.today().isoformat()
    in_7 = date.fromordinal(date.today().toordinal() + 7).isoformat()
    conn = get_db()
    rows = conn.execute(
        """SELECT a.title, p.scheduled_date
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NULL
              AND p.scheduled_date BETWEEN ? AND ?
            ORDER BY p.scheduled_date ASC""",
        (today, in_7),
    ).fetchall()
    conn.close()
    if rows:
        console.print("[bold yellow]Reminder — coming up in the next 7 days:[/bold yellow]")
        for r in rows:
            console.print(f"  • [bold]{r['title']}[/bold]  [dim]{r['scheduled_date']}[/dim]")
        console.print()


def main() -> None:
    init_db()

    console.print(
        Panel(
            "[bold cyan]Fun Activity Planner[/bold cyan]\n"
            "[dim]Your personal adventure organizer[/dim]",
            border_style="cyan",
            expand=False,
        )
    )
    _show_nudges()

    MENU = {
        "1": ("Add a new idea",             capture.add_idea),
        "2": ("Browse my ideas",            browser.browse_ideas),
        "3": ("Plan something",             scheduler.plan_activity),
        "4": ("View upcoming plans",        scheduler.view_upcoming),
        "5": ("Manage steps for a plan",    steps.manage_steps),
        "6": ("Review past activities",     review.review_past),
        "7": ("Surprise me!",               browser.surprise_me),
        "q": ("Quit",                       None),
    }

    while True:
        console.print("\n[bold]What would you like to do?[/bold]")
        for key, (label, _) in MENU.items():
            console.print(f"  [cyan]{key}[/cyan]  {label}")

        choice = Prompt.ask("\nChoice", choices=list(MENU.keys()), default="1")

        if choice == "q":
            console.print("[dim]Goodbye! Go have some fun.[/dim]")
            break

        _, fn = MENU[choice]
        fn()


if __name__ == "__main__":
    main()
