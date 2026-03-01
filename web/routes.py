from datetime import date, datetime, timedelta
from urllib.parse import quote
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from db.database import get_db
from db.models import CATEGORIES, ENERGY_LEVELS, COST_ESTIMATES, DEFAULT_STEPS

bp = Blueprint("main", __name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _activities_with_tags(where: str = "", params: tuple = ()):
    conn = get_db()
    rows = conn.execute(
        """SELECT a.id, a.title, a.description, a.category, a.energy_level,
                  a.cost_estimate, a.status, a.created_at,
                  GROUP_CONCAT(t.name, ', ') AS tags
             FROM activities a
             LEFT JOIN activity_tags at ON at.activity_id = a.id
             LEFT JOIN tags t           ON t.id = at.tag_id
            WHERE 1=1 """ + where + """
            GROUP BY a.id
            ORDER BY a.created_at DESC""",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _plans_with_progress(where: str = "", params: tuple = ()):
    conn = get_db()
    rows = conn.execute(
        """SELECT p.id, a.title, a.category, p.scheduled_date, p.notes,
                  p.completed_at, p.rating, p.reflection,
                  SUM(s.is_done)  AS steps_done,
                  COUNT(s.id)     AS steps_total
             FROM plans p
             JOIN activities a ON a.id = p.activity_id
             LEFT JOIN steps s ON s.plan_id = p.id
            WHERE 1=1 """ + where + """
            GROUP BY p.id
            ORDER BY CASE WHEN p.scheduled_date IS NULL THEN 1 ELSE 0 END,
                     p.scheduled_date ASC""",
        params,
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _valid_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


def _gcal_url(title: str, scheduled_date: str | None, notes: str = "") -> str:
    """Build a Google Calendar 'add event' URL (no API key needed)."""
    if not scheduled_date:
        return ""
    d = date.fromisoformat(scheduled_date)
    d_next = d + timedelta(days=1)
    dates = f"{d.strftime('%Y%m%d')}/{d_next.strftime('%Y%m%d')}"
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    return f"{base}&text={quote(title)}&dates={dates}&details={quote(notes or '')}"


def _ics_response(title: str, scheduled_date: str | None, notes: str = "") -> Response:
    """Return an iCalendar (.ics) file download response."""
    if not scheduled_date:
        return Response("No date set for this plan.", status=400, mimetype="text/plain")
    d = date.fromisoformat(scheduled_date)
    d_next = d + timedelta(days=1)
    uid = f"funplanner-{title.replace(' ', '')}-{d.strftime('%Y%m%d')}@localhost"
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//Fun Planner//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:PUBLISH\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}\r\n"
        f"DTEND;VALUE=DATE:{d_next.strftime('%Y%m%d')}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DESCRIPTION:{(notes or '').replace(chr(10), '\\n')}\r\n"
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    filename = title.replace(" ", "_")[:40] + ".ics"
    return Response(
        ics,
        mimetype="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── dashboard ─────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    today = date.today().isoformat()
    in_7  = date.fromordinal(date.today().toordinal() + 7).isoformat()

    conn = get_db()

    upcoming = conn.execute(
        """SELECT p.id, a.title, p.scheduled_date
             FROM plans p JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NULL
              AND p.scheduled_date BETWEEN ? AND ?
            ORDER BY p.scheduled_date""",
        (today, in_7),
    ).fetchall()

    overdue = conn.execute(
        """SELECT p.id, a.title, p.scheduled_date
             FROM plans p JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NULL
              AND p.scheduled_date < ?
            ORDER BY p.scheduled_date""",
        (today,),
    ).fetchall()

    stats = conn.execute(
        """SELECT
             SUM(CASE WHEN status='idea'    THEN 1 ELSE 0 END) AS ideas,
             SUM(CASE WHEN status='planned' THEN 1 ELSE 0 END) AS planned,
             SUM(CASE WHEN status='done'    THEN 1 ELSE 0 END) AS done
             FROM activities"""
    ).fetchone()

    recent_done = conn.execute(
        """SELECT a.title, p.rating, p.completed_at
             FROM plans p JOIN activities a ON a.id = p.activity_id
            WHERE p.completed_at IS NOT NULL
            ORDER BY p.completed_at DESC LIMIT 5"""
    ).fetchall()

    conn.close()

    return render_template(
        "index.html",
        upcoming=upcoming,
        overdue=overdue,
        stats=stats,
        recent_done=recent_done,
        today=today,
    )


# ── ideas ─────────────────────────────────────────────────────────────────────

@bp.route("/ideas")
def ideas():
    category    = request.args.get("category", "")
    energy      = request.args.get("energy", "")
    cost        = request.args.get("cost", "")
    status      = request.args.get("status", "")
    tag         = request.args.get("tag", "")

    where, params = [], []
    if category: where.append("AND a.category = ?");     params.append(category)
    if energy:   where.append("AND a.energy_level = ?"); params.append(energy)
    if cost:     where.append("AND a.cost_estimate = ?");params.append(cost)
    if status:   where.append("AND a.status = ?");       params.append(status)
    if tag:
        where.append(
            "AND a.id IN (SELECT at2.activity_id FROM activity_tags at2 "
            "JOIN tags t2 ON t2.id = at2.tag_id WHERE t2.name = ?)"
        )
        params.append(tag.lower())

    rows = _activities_with_tags(" ".join(where), tuple(params))

    return render_template(
        "ideas.html",
        ideas=rows,
        categories=CATEGORIES,
        energy_levels=ENERGY_LEVELS,
        cost_estimates=COST_ESTIMATES,
        filters={"category": category, "energy": energy, "cost": cost,
                 "status": status, "tag": tag},
    )


@bp.route("/ideas/add", methods=["GET", "POST"])
def add_idea():
    if request.method == "POST":
        title        = request.form.get("title", "").strip()
        description  = request.form.get("description", "").strip()
        category     = request.form.get("category", "other")
        energy_level = request.form.get("energy_level", "medium")
        cost_estimate= request.form.get("cost_estimate", "cheap")
        tags_raw     = request.form.get("tags", "")
        tags         = [t.strip().lower() for t in tags_raw.split(",") if t.strip()]

        if not title:
            flash("Title is required.", "danger")
            return redirect(url_for("main.add_idea"))

        conn = get_db()
        with conn:
            cur = conn.execute(
                "INSERT INTO activities (title, description, category, energy_level, cost_estimate) VALUES (?,?,?,?,?)",
                (title, description, category, energy_level, cost_estimate),
            )
            aid = cur.lastrowid
            for tag in tags:
                conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                tr = conn.execute("SELECT id FROM tags WHERE name = ?", (tag,)).fetchone()
                conn.execute("INSERT OR IGNORE INTO activity_tags VALUES (?,?)", (aid, tr["id"]))
        conn.close()
        flash(f'Idea "{title}" saved!', "success")
        return redirect(url_for("main.ideas"))

    return render_template(
        "add_idea.html",
        categories=CATEGORIES,
        energy_levels=ENERGY_LEVELS,
        cost_estimates=COST_ESTIMATES,
    )


@bp.route("/ideas/random")
def random_idea():
    import random
    rows = _activities_with_tags("AND a.status = 'idea'")
    if not rows:
        flash("No unplanned ideas yet — add some first!", "warning")
        return redirect(url_for("main.ideas"))
    pick = random.choice(rows)
    return render_template("random_idea.html", idea=pick)


@bp.route("/ideas/<int:idea_id>/delete", methods=["POST"])
def delete_idea(idea_id):
    conn = get_db()
    with conn:
        conn.execute("DELETE FROM activities WHERE id = ?", (idea_id,))
    conn.close()
    flash("Idea deleted.", "info")
    return redirect(url_for("main.ideas"))


# ── planning ──────────────────────────────────────────────────────────────────

@bp.route("/plan", methods=["GET", "POST"])
def plan():
    if request.method == "POST":
        idea_id        = int(request.form["idea_id"])
        scheduled_date = request.form.get("scheduled_date", "").strip()
        notes          = request.form.get("notes", "").strip()
        use_defaults   = request.form.get("use_defaults") == "1"

        if scheduled_date and not _valid_date(scheduled_date):
            flash("Invalid date — saved as TBD.", "warning")
            scheduled_date = ""

        conn = get_db()
        with conn:
            cur = conn.execute(
                "INSERT INTO plans (activity_id, scheduled_date, notes) VALUES (?,?,?)",
                (idea_id, scheduled_date or None, notes),
            )
            plan_id = cur.lastrowid
            conn.execute("UPDATE activities SET status='planned' WHERE id=?", (idea_id,))

            if use_defaults:
                cat = conn.execute("SELECT category FROM activities WHERE id=?", (idea_id,)).fetchone()["category"]
                for i, desc in enumerate(DEFAULT_STEPS.get(cat, DEFAULT_STEPS["other"]), 1):
                    conn.execute(
                        "INSERT INTO steps (plan_id, description, order_index) VALUES (?,?,?)",
                        (plan_id, desc, i),
                    )
        conn.close()
        flash("Plan created!", "success")
        return redirect(url_for("main.steps", plan_id=plan_id))

    ideas = _activities_with_tags("AND a.status = 'idea'")
    return render_template("plan.html", ideas=ideas)


# ── upcoming ──────────────────────────────────────────────────────────────────

@bp.route("/upcoming")
def upcoming():
    plans = _plans_with_progress("AND p.completed_at IS NULL")
    today = date.today().isoformat()
    gcal_urls = {
        p["id"]: _gcal_url(p["title"], p["scheduled_date"], p["notes"])
        for p in plans
    }
    return render_template("upcoming.html", plans=plans, today=today, gcal_urls=gcal_urls)


# ── calendar exports ─────────────────────────────────────────────────────────

@bp.route("/plans/<int:plan_id>/calendar.ics")
def export_ics(plan_id):
    conn = get_db()
    row = conn.execute(
        "SELECT a.title, p.scheduled_date, p.notes FROM plans p "
        "JOIN activities a ON a.id = p.activity_id WHERE p.id = ?",
        (plan_id,),
    ).fetchone()
    conn.close()
    if not row:
        flash("Plan not found.", "danger")
        return redirect(url_for("main.upcoming"))
    return _ics_response(row["title"], row["scheduled_date"], row["notes"])


@bp.route("/steps/<int:step_id>/calendar.ics")
def export_step_ics(step_id):
    conn = get_db()
    row = conn.execute(
        """SELECT s.description, s.due_date, a.title AS plan_title
             FROM steps s
             JOIN plans p ON p.id = s.plan_id
             JOIN activities a ON a.id = p.activity_id
            WHERE s.id = ?""",
        (step_id,),
    ).fetchone()
    conn.close()
    if not row or not row["due_date"]:
        flash("Step has no due date set.", "warning")
        return redirect(request.referrer or url_for("main.upcoming"))
    title = f"{row['description']} ({row['plan_title']})"
    return _ics_response(title, row["due_date"])


# ── steps ─────────────────────────────────────────────────────────────────────

@bp.route("/plans/<int:plan_id>/steps", methods=["GET", "POST"])
def steps(plan_id):
    if request.method == "POST":
        desc     = request.form.get("description", "").strip()
        due_date = request.form.get("due_date", "").strip()
        if not desc:
            flash("Step description is required.", "danger")
            return redirect(url_for("main.steps", plan_id=plan_id))
        if due_date and not _valid_date(due_date):
            due_date = ""
        conn = get_db()
        with conn:
            max_order = conn.execute(
                "SELECT COALESCE(MAX(order_index),0) FROM steps WHERE plan_id=?", (plan_id,)
            ).fetchone()[0]
            conn.execute(
                "INSERT INTO steps (plan_id, description, due_date, order_index) VALUES (?,?,?,?)",
                (plan_id, desc, due_date or None, max_order + 1),
            )
        conn.close()
        flash("Step added.", "success")
        return redirect(url_for("main.steps", plan_id=plan_id))

    conn = get_db()
    plan = conn.execute(
        """SELECT p.id, a.title, a.category, p.scheduled_date, p.notes
             FROM plans p JOIN activities a ON a.id = p.activity_id
            WHERE p.id = ?""",
        (plan_id,),
    ).fetchone()
    step_rows = conn.execute(
        "SELECT * FROM steps WHERE plan_id=? ORDER BY order_index, id", (plan_id,)
    ).fetchall()
    conn.close()

    if not plan:
        flash("Plan not found.", "danger")
        return redirect(url_for("main.upcoming"))

    gcal = _gcal_url(plan["title"], plan["scheduled_date"], plan["notes"])
    step_gcal = {
        s["id"]: _gcal_url(
            f"{s['description']} ({plan['title']})",
            s["due_date"],
        )
        for s in step_rows if s["due_date"]
    }
    return render_template("steps.html", plan=dict(plan),
                           steps=[dict(s) for s in step_rows],
                           gcal_url=gcal,
                           step_gcal=step_gcal)


@bp.route("/steps/<int:step_id>/update", methods=["POST"])
def update_step(step_id):
    due_date = request.form.get("due_date", "").strip()
    if due_date and not _valid_date(due_date):
        due_date = ""
    conn = get_db()
    plan_id = conn.execute("SELECT plan_id FROM steps WHERE id=?", (step_id,)).fetchone()["plan_id"]
    with conn:
        conn.execute("UPDATE steps SET due_date=? WHERE id=?", (due_date or None, step_id))
    conn.close()
    return redirect(url_for("main.steps", plan_id=plan_id))


@bp.route("/plans/<int:plan_id>/set-date", methods=["POST"])
def update_plan_date(plan_id):
    scheduled_date = request.form.get("scheduled_date", "").strip()
    if scheduled_date and not _valid_date(scheduled_date):
        flash("Invalid date format.", "danger")
        return redirect(url_for("main.steps", plan_id=plan_id))
    conn = get_db()
    with conn:
        conn.execute("UPDATE plans SET scheduled_date=? WHERE id=?",
                     (scheduled_date or None, plan_id))
    conn.close()
    return redirect(url_for("main.steps", plan_id=plan_id))


@bp.route("/steps/<int:step_id>/toggle", methods=["POST"])
def toggle_step(step_id):
    conn = get_db()
    plan_id = conn.execute("SELECT plan_id FROM steps WHERE id=?", (step_id,)).fetchone()["plan_id"]
    with conn:
        conn.execute("UPDATE steps SET is_done = 1 - is_done WHERE id=?", (step_id,))
    conn.close()
    return redirect(url_for("main.steps", plan_id=plan_id))


@bp.route("/steps/<int:step_id>/delete", methods=["POST"])
def delete_step(step_id):
    conn = get_db()
    plan_id = conn.execute("SELECT plan_id FROM steps WHERE id=?", (step_id,)).fetchone()["plan_id"]
    with conn:
        conn.execute("DELETE FROM steps WHERE id=?", (step_id,))
    conn.close()
    flash("Step deleted.", "info")
    return redirect(url_for("main.steps", plan_id=plan_id))


@bp.route("/plans/<int:plan_id>/reorder-steps", methods=["POST"])
def reorder_steps(plan_id):
    """Accept JSON list of step IDs in new order, update order_index."""
    from flask import jsonify
    data = request.get_json(silent=True)
    if not data or "order" not in data:
        return jsonify({"error": "bad request"}), 400
    conn = get_db()
    with conn:
        for idx, step_id in enumerate(data["order"], start=1):
            conn.execute("UPDATE steps SET order_index=? WHERE id=? AND plan_id=?",
                         (idx, step_id, plan_id))
    conn.close()
    return jsonify({"ok": True})


# ── review ────────────────────────────────────────────────────────────────────

@bp.route("/review")
def review():
    today = date.today().isoformat()
    overdue = _plans_with_progress(
        "AND p.completed_at IS NULL AND (p.scheduled_date <= ? OR p.scheduled_date IS NULL)",
        (today,),
    )
    history = _plans_with_progress("AND p.completed_at IS NOT NULL")
    history.sort(key=lambda r: r["completed_at"] or "", reverse=True)
    return render_template("review.html", overdue=overdue, history=history[:20])


@bp.route("/review/<int:plan_id>", methods=["POST"])
def submit_review(plan_id):
    did_it     = request.form.get("did_it") == "1"
    skip_it    = request.form.get("skip_it") == "1"
    rating     = request.form.get("rating")
    reflection = request.form.get("reflection", "").strip()

    conn = get_db()
    with conn:
        if did_it:
            conn.execute(
                "UPDATE plans SET completed_at=?, rating=?, reflection=? WHERE id=?",
                (datetime.now().isoformat(), int(rating) if rating else None, reflection, plan_id),
            )
            conn.execute(
                "UPDATE activities SET status='done' WHERE id=(SELECT activity_id FROM plans WHERE id=?)",
                (plan_id,),
            )
            flash("Marked as done! Great job 🎉", "success")
        elif skip_it:
            conn.execute("UPDATE plans SET completed_at=? WHERE id=?",
                         (datetime.now().isoformat(), plan_id))
            conn.execute(
                "UPDATE activities SET status='skipped' WHERE id=(SELECT activity_id FROM plans WHERE id=?)",
                (plan_id,),
            )
            flash("Marked as skipped.", "info")
    conn.close()
    return redirect(url_for("main.review"))
