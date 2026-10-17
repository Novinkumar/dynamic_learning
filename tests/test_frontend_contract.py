from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_required_frontend_assets_exist():
    expected = [
        "app/templates/base.html", "app/templates/auth/login.html", "app/templates/auth/register.html",
        "app/templates/dashboard.html", "app/templates/quiz.html", "app/templates/library.html",
        "app/templates/evaluation.html", "app/static/css/app.css", "app/static/js/app.js",
    ]
    assert all((ROOT / path).is_file() for path in expected)


def test_templates_expose_accessible_and_adaptive_controls():
    dashboard = (ROOT / "app/templates/dashboard.html").read_text(encoding="utf-8")
    quiz = (ROOT / "app/templates/quiz.html").read_text(encoding="utf-8")
    library = (ROOT / "app/templates/library.html").read_text(encoding="utf-8")
    assert "aria-label=\"Learning summary\"" in dashboard
    assert "data-quiz" in quiz and "required" in quiz
    assert "name=\"q\"" in library and "Clear filters" in library
