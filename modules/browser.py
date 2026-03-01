"""Browse, filter, and randomly suggest activity ideas."""
import random
from rich.prompt import Prompt
from db.database import get_db
from db.models import CATEGORIES, ENERGY_LEVELS, COST_ESTIMATES
from utils.display import console, section, activity_table


_IDEAS_QUERY = """
    SELECT a.id, a.title, a.category, a.energy_level, a.cost_estimate, a.status,
           GROUP_CONCAT(t.name, ', ') AS tags
      FROM activities a
      LEFT JOIN activity_tags at ON at.activity_id = a.id
      LEFT JOIN tags t           ON t.id = at.tag_id
     WHERE 1=1
"""


def _fetch_ideas(where_extra: str = "", params: tuple = ()) -> list:
    conn = get_db()
    rows = conn.execute(
        _IDEAS_QUERY + where_extra + " GROUP BY a.id ORDER BY a.created_at DESC",
        params,
    ).fetchall()
    conn.close()
    return rows


def browse_ideas() -> None:
    section("Browse Ideas", "cyan")

    console.print(
        "\nFilter by: [cyan]1[/cyan] All  [cyan]2[/cyan] Category  "
        "[cyan]3[/cyan] Energy  [cyan]4[/cyan] Cost  [cyan]5[/cyan] Status  [cyan]6[/cyan] Tag"
    )
    choice = Prompt.ask("Filter", choices=["1", "2", "3", "4", "5", "6"], default="1")

    where, params = "", ()

    if choice == "2":
        cat_display = "  ".join(f"[cyan]{i+1}[/cyan] {c}" for i, c in enumerate(CATEGORIES))
        console.print(cat_display)
        idx = int(Prompt.ask("Category", choices=[str(i + 1) for i in range(len(CATEGORIES))], default="1")) - 1
        where, params = " AND a.category = ?", (CATEGORIES[idx],)

    elif choice == "3":
        console.print("[cyan]1[/cyan] low  [cyan]2[/cyan] medium  [cyan]3[/cyan] high")
        idx = int(Prompt.ask("Energy level", choices=["1", "2", "3"], default="2")) - 1
        where, params = " AND a.energy_level = ?", (ENERGY_LEVELS[idx],)

    elif choice == "4":
        console.print("[cyan]1[/cyan] free  [cyan]2[/cyan] cheap  [cyan]3[/cyan] moderate  [cyan]4[/cyan] expensive")
        idx = int(Prompt.ask("Cost estimate", choices=["1", "2", "3", "4"], default="1")) - 1
        where, params = " AND a.cost_estimate = ?", (COST_ESTIMATES[idx],)

    elif choice == "5":
        console.print("[cyan]1[/cyan] idea  [cyan]2[/cyan] planned  [cyan]3[/cyan] done  [cyan]4[/cyan] skipped")
        status_map = {"1": "idea", "2": "planned", "3": "done", "4": "skipped"}
        s = Prompt.ask("Status", choices=list(status_map.keys()), default="1")
        where, params = " AND a.status = ?", (status_map[s],)

    elif choice == "6":
        tag = Prompt.ask("Tag name").strip().lower()
        where = " AND a.id IN (SELECT activity_id FROM activity_tags at2 JOIN tags t2 ON t2.id = at2.tag_id WHERE t2.name = ?)"
        params = (tag,)

    rows = _fetch_ideas(where, params)

    if not rows:
        console.print("[yellow]No ideas found matching those filters.[/yellow]")
        return

    console.print(activity_table(rows))
    console.print(f"[dim]{len(rows)} idea(s) found.[/dim]")


def surprise_me() -> None:
    section("Surprise Me! 🎲", "magenta")
    rows = _fetch_ideas(" AND a.status = 'idea'")
    if not rows:
        console.print("[yellow]No unplanned ideas in the backlog yet. Add some first![/yellow]")
        return

    pick = random.choice(rows)
    console.print(f"\n[bold magenta]How about:[/bold magenta]  [bold]{pick['title']}[/bold]")
    console.print(f"  Category : [cyan]{pick['category']}[/cyan]")
    console.print(f"  Energy   : {pick['energy_level']}")
    console.print(f"  Cost     : {pick['cost_estimate']}")
    if pick["description"]:
        console.print(f"  Notes    : [dim]{pick['description']}[/dim]")
    if pick["tags"]:
        console.print(f"  Tags     : [dim]{pick['tags']}[/dim]")
