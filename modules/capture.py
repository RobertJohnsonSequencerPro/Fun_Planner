"""Idea capture flow — prompts the user for a new activity and saves it."""
from rich.prompt import Prompt, Confirm
from db.database import get_db
from db.models import CATEGORIES, ENERGY_LEVELS, COST_ESTIMATES
from utils.display import console, section


def add_idea() -> None:
    section("Add a New Idea", "green")

    title = Prompt.ask("[bold]Title[/bold]").strip()
    if not title:
        console.print("[red]Title cannot be empty — idea not saved.[/red]")
        return

    description = Prompt.ask("Short description [dim](optional)[/dim]", default="").strip()

    # Category
    cat_display = "  ".join(f"[cyan]{i+1}[/cyan] {c}" for i, c in enumerate(CATEGORIES))
    console.print(f"\nCategories: {cat_display}")
    cat_idx = int(Prompt.ask("Category", choices=[str(i + 1) for i in range(len(CATEGORIES))], default="8")) - 1
    category = CATEGORIES[cat_idx]

    # Energy
    console.print("\nEnergy level: [cyan]1[/cyan] low  [cyan]2[/cyan] medium  [cyan]3[/cyan] high")
    energy_idx = int(Prompt.ask("Energy level", choices=["1", "2", "3"], default="2")) - 1
    energy_level = ENERGY_LEVELS[energy_idx]

    # Cost
    console.print("\nCost estimate: [cyan]1[/cyan] free  [cyan]2[/cyan] cheap  [cyan]3[/cyan] moderate  [cyan]4[/cyan] expensive")
    cost_idx = int(Prompt.ask("Cost estimate", choices=["1", "2", "3", "4"], default="2")) - 1
    cost_estimate = COST_ESTIMATES[cost_idx]

    # Tags
    tags_raw = Prompt.ask("\nTags [dim](comma-separated, e.g. summer,weekend — optional)[/dim]", default="")
    tags = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]

    conn = get_db()
    with conn:
        cur = conn.execute(
            """INSERT INTO activities (title, description, category, energy_level, cost_estimate)
               VALUES (?, ?, ?, ?, ?)""",
            (title, description, category, energy_level, cost_estimate),
        )
        activity_id = cur.lastrowid

        for tag in tags:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            tag_row = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO activity_tags (activity_id, tag_id) VALUES (?, ?)",
                (activity_id, tag_row["id"]),
            )
    conn.close()

    console.print(f"\n[bold green]✓ Idea '[italic]{title}[/italic]' saved! (id={activity_id})[/bold green]")
