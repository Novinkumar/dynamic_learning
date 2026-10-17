"""Build the six report diagrams for Dynamic Learning.

This file intentionally has no application imports.  It is a standalone,
offline renderer so the report assets can be regenerated without changing the
Flask project.  Semantics are taken from README.md, app/models.py, and
app/routes/learning.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

# 1600 x 1000 pixels.  At a 6.25-inch report width this is approximately
# 256 dpi, while the generous point sizes remain readable in print.
FIGSIZE = (12.8, 8.0)
DPI = 125

INK = "#18372C"
GREEN = "#1E604B"
GREEN_2 = "#2C8164"
PALE = "#E7F2ED"
PALE_2 = "#F4F8F6"
MUTED = "#5B7068"
LINE = "#6B847B"
OCHRE = "#B87524"
OCHRE_PALE = "#FFF1DE"
RED = "#A64E45"
RED_PALE = "#FCEBE8"
REF_FILL = "#F8FAF9"
REF_LINE = "#7E958D"
WHITE = "#FFFFFF"


def new_figure():
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    return fig, ax


def header(ax, figure: str, title: str, subtitle: str):
    ax.text(0.7, 9.72, figure, color=GREEN_2, fontsize=13.5, fontweight="bold", va="top")
    ax.text(0.7, 9.36, title, color=INK, fontsize=22, fontweight="bold", va="top")
    ax.text(0.72, 8.96, subtitle, color=MUTED, fontsize=10.2, va="top")
    ax.plot([0.7, 15.3], [8.68, 8.68], color=GREEN, lw=1.5)


def save(fig, filename: str):
    fig.savefig(OUT / filename, dpi=DPI, facecolor=WHITE, edgecolor="none")
    plt.close(fig)


def rounded_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    lines: Sequence[str] = (),
    *,
    fill: str = PALE,
    edge: str = GREEN,
    title_color: str = GREEN,
    title_size: float = 13.2,
    body_size: float = 10.2,
    dashed: bool = False,
):
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.035,rounding_size=0.12",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=fill,
        linestyle="--" if dashed else "-",
        zorder=2,
    )
    ax.add_patch(box)
    ax.add_patch(Rectangle((x, y), 0.075, h, color=edge, lw=0, zorder=3))
    ax.text(
        x + 0.23,
        y + h - 0.24,
        title,
        color=title_color,
        fontsize=title_size,
        fontweight="bold",
        va="top",
        ha="left",
        zorder=4,
    )
    if lines:
        ax.text(
            x + 0.23,
            y + h - 0.46,
            "\n".join(f"- {line}" for line in lines),
            color=INK,
            fontsize=body_size,
            linespacing=1.35,
            va="top",
            ha="left",
            zorder=4,
        )


def panel(ax, x: float, y: float, w: float, h: float, title: str, subtitle: str = ""):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.025,rounding_size=0.14",
        facecolor=WHITE,
        edgecolor=GREEN,
        linewidth=1.2,
        linestyle="--",
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(x + 0.22, y + h - 0.18, title, color=GREEN, fontsize=11.8, fontweight="bold", va="top")
    if subtitle:
        ax.text(x + 0.22, y + h - 0.47, subtitle, color=MUTED, fontsize=8.4, va="top")


def arrow(
    ax,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    color: str = GREEN_2,
    lw: float = 1.5,
    label: str | None = None,
    label_offset: tuple[float, float] = (0.0, 0.12),
    rad: float = 0.0,
    label_size: float = 8.8,
    style: str = "-|>",
):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=11,
        linewidth=lw,
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        zorder=1,
    )
    ax.add_patch(patch)
    if label:
        mx = (start[0] + end[0]) / 2 + label_offset[0]
        my = (start[1] + end[1]) / 2 + label_offset[1]
        ax.text(
            mx,
            my,
            label,
            color=MUTED,
            fontsize=label_size,
            ha="center",
            va="center",
            bbox={"facecolor": WHITE, "edgecolor": "none", "pad": 1.5},
            zorder=5,
        )


def dashed_feedback(ax, start, end, label: str):
    arrow(ax, start, end, color=LINE, lw=1.2, label=label, style="-|>", label_size=8.4)
    # Overlay a short dash pattern by drawing a second line underneath the arrowhead.
    ax.plot([start[0], end[0]], [start[1], end[1]], color=LINE, lw=1.0, ls=(0, (4, 3)), zorder=0)


def actor(ax, x: float, y: float, label: str, color: str = GREEN):
    ax.add_patch(Circle((x, y + 0.55), 0.16, fill=False, ec=color, lw=1.8, zorder=3))
    ax.plot([x, x], [y + 0.39, y - 0.12], color=color, lw=1.8, zorder=3)
    ax.plot([x - 0.28, x + 0.28], [y + 0.20, y + 0.20], color=color, lw=1.8, zorder=3)
    ax.plot([x, x - 0.24], [y - 0.12, y - 0.46], color=color, lw=1.8, zorder=3)
    ax.plot([x, x + 0.24], [y - 0.12, y - 0.46], color=color, lw=1.8, zorder=3)
    ax.text(x, y - 0.70, label, ha="center", va="top", fontsize=11.2, color=INK, fontweight="bold")


def use_case(ax, x: float, y: float, w: float, h: float, label: str, *, kind: str = "green"):
    fill, edge = (OCHRE_PALE, OCHRE) if kind == "ochre" else (PALE, GREEN_2)
    ax.add_patch(Ellipse((x, y), w, h, facecolor=fill, edgecolor=edge, lw=1.4, zorder=2))
    ax.text(x, y, label, ha="center", va="center", fontsize=10.0, color=INK, linespacing=1.25, zorder=3)


def association(ax, start, end, *, color: str = LINE, lw: float = 1.2, rad: float = 0.0):
    """Draw an actor association on top of the boundary so its endpoints are visible."""
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-",
            linewidth=lw,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
            zorder=4,
        )
    )


def entity(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    name: str,
    fields: Sequence[str],
    *,
    accent: str = GREEN_2,
    ref: bool = False,
):
    fill = REF_FILL if ref else PALE_2
    edge = REF_LINE if ref else accent
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=edge, linewidth=1.2, linestyle="--" if ref else "-", zorder=2))
    ax.add_patch(Rectangle((x, y + h - 0.30), w, 0.30, facecolor=edge, edgecolor=edge, linewidth=0, zorder=3))
    ax.text(x + w / 2, y + h - 0.15, name, ha="center", va="center", fontsize=8.8 if len(name) > 15 else 10.0, color=WHITE, fontweight="bold", zorder=4)
    ax.text(x + 0.12, y + h - 0.52, "\n".join(fields), ha="left", va="top", fontsize=8.0, color=INK, linespacing=1.25, zorder=4)


def link(ax, start, end, label: str, *, rad: float = 0.0, color: str = LINE, offset=(0, 0.10)):
    arrow(ax, start, end, color=color, lw=1.05, label=label, label_offset=offset, rad=rad, label_size=7.7)


def build_architecture():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.1", "Dynamic Learning application architecture", "Routes coordinate learner actions; both routes and services use SQLAlchemy-backed persistence.")
    rounded_box(ax, 0.75, 4.95, 2.55, 1.75, "Browser / UI", ["Jinja templates", "CSS + progressive JS", "Learner forms"], title_size=14.0)
    rounded_box(ax, 4.05, 4.60, 3.05, 2.45, "Flask blueprints", ["Auth", "Dashboard", "Learning", "Evaluation", "Session + access control"], title_size=14.0)
    rounded_box(ax, 8.00, 5.00, 3.10, 1.75, "Domain services", ["Mastery EMA", "Recommendation ranker", "Evaluation metrics", "Transparent reasons"], title_size=14.0)
    rounded_box(ax, 11.90, 5.00, 2.45, 1.75, "SQLAlchemy", ["Models + relationships", "Transactions", "Query boundary"], title_size=14.0)
    rounded_box(ax, 11.55, 1.65, 3.10, 1.35, "SQLite", ["Default local runtime", "Configured relational store"], fill=OCHRE_PALE, edge=OCHRE, title_color=OCHRE, title_size=14.0)
    rounded_box(ax, 7.85, 1.65, 3.25, 1.35, "PostgreSQL", ["README deployment option", "Not tested in this review"], fill=REF_FILL, edge=REF_LINE, title_color=REF_LINE, title_size=13.2, dashed=True)

    arrow(ax, (3.30, 5.82), (4.05, 5.82), label="HTTP / JSON", label_size=8.3)
    arrow(ax, (7.10, 5.90), (8.00, 5.90), label="orchestrates", label_size=8.3)
    arrow(ax, (11.10, 5.58), (11.90, 5.58), color=GREEN_2, label="service queries", label_offset=(0, -0.18), label_size=8.3)
    arrow(ax, (13.12, 5.00), (13.12, 3.20), color=GREEN_2, label="read / write", label_offset=(0.38, 0), label_size=8.3)
    # Route code can query ORM models directly.  The connector deliberately
    # travels below the services box rather than implying a service-only path.
    ax.plot([7.10, 7.55, 7.55, 11.55], [4.82, 4.82, 3.85, 3.85], color=LINE, lw=1.2, zorder=1)
    arrow(ax, (11.55, 3.85), (11.90, 5.00), color=LINE, label="routes: direct ORM access", label_offset=(0.0, -0.16), label_size=8.0)
    arrow(ax, (11.55, 2.32), (11.10, 2.32), color=REF_LINE, style="-|>", label="alternative", label_offset=(0, 0.15), label_size=8.3)
    dashed_feedback(ax, (8.00, 5.15), (3.30, 5.15), "responses + recommendations")

    ax.text(0.85, 3.05, "The learning blueprint accepts completion and quiz actions.\nCompletion persists completion + interaction; quiz submission also updates mastery and the next-step plan.", color=MUTED, fontsize=9.7, va="top")
    ax.text(8.0, 0.72, "Solid = reviewed implementation   |   Dashed = documented, unverified deployment option", color=MUTED, fontsize=8.9, va="center")
    save(fig, "fig_4_1_architecture.png")


def build_workflow():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.2", "Learner workflow: completion and quiz paths", "The two evidence paths are intentionally separate: resource completion does not grade a quiz or update mastery.")

    rounded_box(ax, 0.75, 6.75, 2.5, 1.15, "1. Sign in / register", ["Create session", "Open overview"], title_size=12.6, body_size=9.5)
    rounded_box(ax, 4.00, 6.75, 2.5, 1.15, "2. Review dashboard", ["Cold-start queue", "Primary + support"], title_size=12.6, body_size=9.5)
    rounded_box(ax, 7.25, 6.75, 2.5, 1.15, "3. Choose activity", ["Resource or quiz", "Follow next step"], title_size=12.6, body_size=9.5)
    arrow(ax, (3.25, 7.33), (4.00, 7.33))
    arrow(ax, (6.50, 7.33), (7.25, 7.33))

    # Completion lane — no mastery update and no quiz re-ranking call.
    panel(ax, 0.55, 3.45, 7.2, 2.55, "RESOURCE COMPLETION", "POST /api/resources/<id>/complete")
    rounded_box(ax, 0.85, 4.15, 1.65, 0.95, "Open resource", ["External URL"], title_size=11.0, body_size=8.7)
    rounded_box(ax, 2.85, 4.15, 1.75, 0.95, "Mark complete", ["POST completion"], title_size=11.0, body_size=8.7)
    rounded_box(ax, 4.95, 4.15, 2.35, 0.95, "Write completion", ["ResourceCompletion", "ResourceInteraction"], title_size=11.0, body_size=8.5)
    arrow(ax, (2.50, 4.62), (2.85, 4.62))
    arrow(ax, (4.60, 4.62), (4.95, 4.62))
    ax.text(0.85, 3.70, "No quiz rows, no mastery update, and no quiz adaptation response.", color=MUTED, fontsize=8.8, va="center")

    # Quiz lane — actual order from submit_quiz.
    panel(ax, 7.95, 3.45, 7.5, 2.55, "QUIZ SUBMISSION", "POST /api/quizzes/<id>/submit")
    rounded_box(ax, 8.20, 4.15, 1.40, 0.95, "Open quiz", ["Questions"], title_size=11.0, body_size=8.7)
    rounded_box(ax, 9.90, 4.15, 1.60, 0.95, "Validate + grade", ["Payload", "score"], title_size=10.8, body_size=8.5)
    rounded_box(ax, 11.80, 4.15, 1.55, 0.95, "Atomic write", ["Attempt + response", "MasteryScore"], title_size=10.4, body_size=8.0)
    rounded_box(ax, 13.65, 4.15, 1.55, 0.95, "Re-rank + respond", ["Next plan + feedback"], title_size=9.3, body_size=7.8)
    arrow(ax, (9.60, 4.62), (9.90, 4.62))
    arrow(ax, (11.50, 4.62), (11.80, 4.62))
    arrow(ax, (13.35, 4.62), (13.65, 4.62))
    ax.text(8.20, 3.70, "new = old + 0.35 * (score - old), clamped to [0, 1]", color=MUTED, fontsize=8.8, va="center")

    arrow(ax, (8.50, 6.75), (8.50, 6.00), color=GREEN_2, label="quiz", label_offset=(0.35, 0), label_size=8.0)
    arrow(ax, (8.00, 6.75), (2.00, 6.00), color=GREEN_2, label="resource", label_offset=(0, 0.20), rad=0.08, label_size=8.0)
    ax.text(0.85, 1.55, "The learner returns to the overview after either path; only the quiz path produces score, mastery, and recommendation-adaptation feedback.", color=MUTED, fontsize=9.5, va="center")
    save(fig, "fig_4_2_workflow.png")


def build_use_case():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.3", "Use-case view", "Actors are connected directly to the system capabilities they invoke or support.")
    boundary = FancyBboxPatch((3.15, 1.05), 9.85, 7.15, boxstyle="round,pad=0.03,rounding_size=0.15", facecolor=WHITE, edgecolor=GREEN, linewidth=1.5, linestyle="--")
    ax.add_patch(boundary)
    ax.text(3.45, 7.92, "DYNAMIC LEARNING SYSTEM", color=GREEN, fontsize=12, fontweight="bold", va="top")

    actor(ax, 1.55, 5.45, "Learner")
    actor(ax, 14.55, 6.50, "Admin", color=OCHRE)
    actor(ax, 14.55, 2.55, "External resource", color=REF_LINE)

    use_case(ax, 5.05, 6.75, 2.35, 0.75, "Register /\nsign in")
    use_case(ax, 8.00, 6.75, 2.65, 0.75, "Browse + filter\nlibrary")
    use_case(ax, 10.95, 6.75, 2.55, 0.75, "View dashboard +\nrecommendations")
    use_case(ax, 5.05, 4.95, 2.55, 0.75, "Open external\nresource")
    use_case(ax, 8.00, 4.95, 2.65, 0.75, "Mark resource\ncomplete")
    use_case(ax, 10.95, 4.95, 2.55, 0.75, "Take quiz +\nsubmit answers")
    use_case(ax, 8.00, 3.05, 2.85, 0.75, "View score, mastery,\nand next step")
    use_case(ax, 10.95, 1.60, 2.55, 0.75, "Review evaluation\nmetrics", kind="ochre")

    # Actor associations terminate on the ellipse boundary, not in empty space.
    association(ax, (1.82, 6.05), (3.88, 6.78))
    association(ax, (1.82, 6.00), (6.65, 6.78))
    association(ax, (1.82, 5.92), (9.70, 6.78))
    association(ax, (1.82, 5.80), (3.78, 5.05))
    association(ax, (1.82, 5.72), (6.70, 5.05))
    association(ax, (1.82, 5.65), (9.68, 5.05))
    association(ax, (1.82, 5.55), (6.60, 3.22))
    association(ax, (1.82, 5.48), (9.55, 3.22))
    association(ax, (14.20, 6.70), (12.25, 1.83), color=OCHRE, lw=1.25)
    # Route the external-resource association below the use-case row so it
    # reaches the Open external resource oval without crossing other ovals.
    association(ax, (14.20, 2.90), (13.05, 2.90), color=REF_LINE, lw=1.25)
    association(ax, (13.05, 2.90), (13.05, 4.22), color=REF_LINE, lw=1.25)
    association(ax, (13.05, 4.22), (6.30, 4.22), color=REF_LINE, lw=1.25)
    association(ax, (6.30, 4.22), (6.12, 4.66), color=REF_LINE, lw=1.25)
    save(fig, "fig_4_3_use_case.png")


def build_data_model():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.4", "Core data model", "Only declared foreign-key links are shown. Reference copies are marked [ref] to keep association lines legible.")

    panel(ax, 0.35, 5.15, 15.30, 3.25, "CATALOG + QUIZ STRUCTURE", "Parent-to-child links use 1:N; Prerequisite has two Topic foreign keys.")
    entity(ax, 0.75, 6.15, 2.20, 1.30, "TOPIC", ["PK id", "name", "description"])
    entity(ax, 3.45, 6.15, 2.20, 1.30, "RESOURCE", ["PK id", "FK topic_id", "title, url", "kind, difficulty"])
    entity(ax, 6.15, 6.15, 2.20, 1.30, "QUIZ", ["PK id", "FK topic_id", "title"])
    entity(ax, 8.85, 6.15, 2.20, 1.30, "QUESTION", ["PK id", "FK quiz_id", "prompt, options"])
    entity(ax, 11.60, 6.15, 3.15, 1.30, "PREREQUISITE", ["PK id", "FK topic_id", "FK prerequisite_id", "minimum_mastery"])
    link(ax, (2.95, 7.34), (3.45, 7.34), "1:N topic_id", offset=(0, 0.23))
    link(ax, (2.95, 7.38), (6.15, 7.38), "1:N topic_id", rad=-0.10, offset=(0, 0.30))
    link(ax, (8.35, 7.34), (8.85, 7.34), "1:N quiz_id", offset=(0, 0.23))
    link(ax, (2.95, 7.42), (11.60, 7.42), "1:N topic_id", rad=-0.10, offset=(0, 0.34))
    link(ax, (2.95, 6.18), (11.60, 6.18), "1:N prerequisite_id", rad=0.12, offset=(0, -0.28))

    panel(ax, 0.35, 0.55, 7.35, 4.15, "QUIZ ACTIVITY RECORDS", "Reference copies are the same Quiz and Question tables above.")
    entity(ax, 0.70, 3.15, 1.65, 0.95, "USER", ["PK id", "email, name"], accent=GREEN)
    entity(ax, 2.75, 3.15, 1.95, 0.95, "QUIZ [ref]", ["PK id"], ref=True)
    entity(ax, 5.10, 3.15, 1.95, 0.95, "QUESTION [ref]", ["PK id"], ref=True)
    entity(ax, 0.70, 1.05, 2.25, 1.35, "QUIZ_ATTEMPT", ["PK id", "FK user_id", "FK quiz_id", "score, answers"], accent=OCHRE)
    entity(ax, 3.70, 1.05, 2.80, 1.35, "QUESTION_RESPONSE", ["PK id", "FK attempt_id", "FK question_id", "answer, is_correct"])
    link(ax, (2.35, 3.55), (0.70, 2.05), "1:N user_id", rad=0.12, offset=(-0.20, 0.06))
    link(ax, (3.72, 3.15), (2.15, 2.40), "1:N quiz_id", rad=0.08, offset=(0.05, 0.18))
    link(ax, (2.95, 1.72), (3.70, 1.72), "1:N attempt_id", offset=(0, 0.14))
    link(ax, (6.05, 3.15), (6.50, 2.15), "1:N question_id", rad=-0.08, offset=(0.18, 0.05))

    panel(ax, 7.95, 0.55, 7.70, 4.15, "RESOURCE + MASTERY RECORDS", "Completion and interaction records are independent foreign-key associations.")
    entity(ax, 8.25, 3.15, 1.55, 0.95, "USER [ref]", ["PK id"], ref=True)
    entity(ax, 10.15, 3.15, 1.75, 0.95, "RESOURCE [ref]", ["PK id"], ref=True)
    entity(ax, 12.30, 3.15, 1.55, 0.95, "TOPIC [ref]", ["PK id"], ref=True)
    entity(ax, 8.25, 1.05, 2.05, 1.35, "RESOURCE_COMPLETION", ["PK id", "FK user_id", "FK resource_id", "completed_at"], accent=GREEN)
    entity(ax, 10.75, 1.05, 2.05, 1.35, "RESOURCE_INTERACTION", ["PK id", "FK user_id", "FK resource_id", "event, created_at"], accent=GREEN)
    entity(ax, 13.25, 1.05, 2.05, 1.35, "MASTERY_SCORE", ["PK id", "FK user_id", "FK topic_id", "score, updated_at"], accent=GREEN)
    link(ax, (9.02, 3.15), (9.02, 2.40), "1:N user_id", offset=(0.35, 0))
    link(ax, (11.02, 3.15), (9.95, 2.40), "1:N resource_id", rad=0.10, offset=(-0.10, 0.12))
    link(ax, (9.02, 3.15), (11.70, 2.40), "1:N user_id", rad=-0.08, offset=(0, 0.15))
    link(ax, (11.02, 3.15), (11.70, 2.40), "1:N resource_id", offset=(0.45, 0.04))
    link(ax, (9.02, 3.15), (13.95, 2.40), "1:N user_id", rad=-0.12, offset=(0, 0.15))
    link(ax, (13.08, 3.15), (14.25, 2.40), "1:N topic_id", rad=-0.05, offset=(0.12, 0.08))

    ax.text(0.55, 0.23, "Reference copies are visual aids only; each [ref] is the corresponding entity in the catalog panel.", color=MUTED, fontsize=8.6, va="center")
    save(fig, "fig_4_4_data_model.png")


def decision(ax, x: float, y: float, w: float, h: float, text: str):
    points = [(x, y + h / 2), (x + w / 2, y), (x + w, y + h / 2), (x + w / 2, y + h)]
    ax.add_patch(Polygon(points, closed=True, facecolor=PALE, edgecolor=GREEN_2, linewidth=1.5, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10.3, fontweight="bold", color=INK, zorder=3)


def build_activity():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.5", "Quiz submission activity", "Valid submissions grade first, then commit attempt, responses, and mastery before recalculating the next plan.")
    ax.add_patch(Circle((8.0, 8.05), 0.18, color=GREEN, zorder=3))
    arrow(ax, (8.0, 7.87), (8.0, 7.58))
    rounded_box(ax, 6.55, 6.88, 2.90, 0.70, "Submit quiz answers", ["JSON answers"], title_size=12.0, body_size=8.7)
    arrow(ax, (8.0, 6.88), (8.0, 6.60))
    rounded_box(ax, 6.55, 5.92, 2.90, 0.70, "Validate payload", ["body, IDs, options"], title_size=12.0, body_size=8.5)
    arrow(ax, (8.0, 5.92), (8.0, 5.62))
    decision(ax, 6.65, 4.75, 2.70, 0.82, "Valid?")
    arrow(ax, (8.0, 4.75), (8.0, 4.46), label="yes", label_offset=(0.34, 0), label_size=8.5)
    rounded_box(ax, 6.55, 3.78, 2.90, 0.70, "Grade questions", ["score + feedback"], title_size=12.0, body_size=8.5)
    arrow(ax, (8.0, 3.78), (8.0, 3.45))
    rounded_box(ax, 6.05, 2.40, 3.90, 0.85, "Atomic database write", ["QuizAttempt + QuestionResponse", "MasteryScore update; commit"], title_size=12.0, body_size=8.5)
    arrow(ax, (8.0, 2.40), (8.0, 2.12))
    rounded_box(ax, 6.55, 1.45, 2.90, 0.62, "Re-rank next plan", ["after commit"], title_size=11.5, body_size=8.2)
    arrow(ax, (8.0, 1.45), (8.0, 1.18))
    rounded_box(ax, 6.55, 0.52, 2.90, 0.62, "Return response", ["score + mastery + next step"], title_size=11.5, body_size=7.9)
    arrow(ax, (9.35, 5.16), (11.05, 5.16), label="no", color=RED, label_offset=(0, 0.15), label_size=8.5)
    rounded_box(ax, 11.05, 4.65, 2.55, 0.95, "Return 400 / 422", ["invalid body, ID, option", "or empty quiz"], fill=RED_PALE, edge=RED, title_color=RED, title_size=11.2, body_size=8.5)
    arrow(ax, (12.32, 4.65), (12.32, 3.65), color=RED, label="error", label_offset=(0.35, 0), label_size=8.5)
    ax.add_patch(Circle((8.0, 0.34), 0.14, color=GREEN, zorder=3))
    ax.add_patch(Circle((12.32, 3.40), 0.14, color=RED, zorder=3))
    arrow(ax, (8.0, 0.52), (8.0, 0.48), color=GREEN)
    ax.text(8.0, 0.16, "end", ha="center", va="top", fontsize=8.8, color=MUTED)
    ax.text(12.32, 3.18, "end", ha="center", va="top", fontsize=8.8, color=MUTED)
    save(fig, "fig_4_5_activity.png")


def lifeline(ax, x: float, label: str):
    ax.text(x, 8.37, label, ha="center", va="center", fontsize=11.3, color=GREEN, fontweight="bold")
    ax.plot([x, x], [8.05, 1.15], color=LINE, lw=1.0, ls=(0, (4, 3)), zorder=0)


def sequence_arrow(ax, x1: float, x2: float, y: float, label: str, *, color: str = GREEN_2, reverse: bool = False):
    start, end = ((x1, y), (x2, y)) if not reverse else ((x2, y), (x1, y))
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, linewidth=1.25, color=color, zorder=2))
    # Labels sit above the message line in a white-backed text box, never on the arrow.
    ax.text((x1 + x2) / 2, y + 0.16, label, ha="center", va="bottom", fontsize=8.3, color=INK, linespacing=1.15, bbox={"facecolor": WHITE, "edgecolor": "none", "pad": 1.8}, zorder=5)


def sequence_internal(ax, x: float, y: float, label: str):
    """Draw a short self-message for validation/grading inside the blueprint."""
    ax.add_patch(FancyArrowPatch((x, y), (x + 0.58, y), arrowstyle="-|>", mutation_scale=9, linewidth=1.2, color=GREEN_2, zorder=2))
    ax.text(x + 0.29, y + 0.16, label, ha="center", va="bottom", fontsize=8.3, color=INK, bbox={"facecolor": WHITE, "edgecolor": "none", "pad": 1.8}, zorder=5)


def build_sequence():
    fig, ax = new_figure()
    header(ax, "FIGURE 4.6", "Quiz submission sequence", "The transaction commits before the post-submit mastery read and recommendation-plan recalculation.")
    xs = [1.55, 5.00, 8.55, 12.20]
    labels = ["Browser / UI", "Learning blueprint", "Mastery +\nrecommender", "SQLAlchemy / DB"]
    for x, label in zip(xs, labels):
        lifeline(ax, x, label)

    sequence_arrow(ax, xs[0], xs[1], 7.72, "1  POST answers")
    sequence_arrow(ax, xs[1], xs[3], 7.18, "2  load quiz, questions,\nprior attempt")
    sequence_arrow(ax, xs[1], xs[3], 6.64, "3  quiz data + prior attempt", reverse=True)
    sequence_arrow(ax, xs[1], xs[2], 6.10, "4  read prior mastery +\npre-submit plan")
    sequence_arrow(ax, xs[1], xs[2], 5.56, "5  snapshots", reverse=True)
    sequence_internal(ax, xs[1], 5.02, "6  validate + grade")
    sequence_arrow(ax, xs[1], xs[3], 4.48, "7  insert attempt +\nquestion responses")
    sequence_arrow(ax, xs[1], xs[2], 3.94, "8  update mastery\n(commit=False)")
    sequence_arrow(ax, xs[2], xs[3], 3.40, "9  persist MasteryScore")
    sequence_arrow(ax, xs[1], xs[3], 2.86, "10  COMMIT transaction")
    sequence_arrow(ax, xs[1], xs[3], 2.32, "11  committed state", reverse=True)
    sequence_arrow(ax, xs[1], xs[2], 1.78, "12  recompute next plan\nafter commit")
    sequence_arrow(ax, xs[1], xs[0], 1.24, "13  JSON: score, feedback,\nmastery, adaptation")
    ax.text(0.75, 0.45, "Internal blueprint steps are shown explicitly so the commit boundary is visible before the next-plan calculation.", color=MUTED, fontsize=9.0, va="center")
    save(fig, "fig_4_6_sequence.png")


def main():
    build_architecture()
    build_workflow()
    build_use_case()
    build_data_model()
    build_activity()
    build_sequence()
    print(f"Wrote six diagrams to {OUT}")


if __name__ == "__main__":
    main()
