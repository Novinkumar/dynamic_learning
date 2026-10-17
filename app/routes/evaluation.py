from flask import Blueprint, jsonify, render_template
from .common import admin_required
from ..services.metrics import evaluation_metrics
from ..services.offline_evaluation import run_offline_evaluation

evaluation_bp = Blueprint("evaluation", __name__)


def evaluation_report():
    """Combine observed application activity with the read-only benchmark."""
    return {**evaluation_metrics(), "offline": run_offline_evaluation(k=5)}


@evaluation_bp.get("/evaluation")
@admin_required
def evaluation_page():
    payload = evaluation_report()
    try: return render_template("evaluation.html", metrics=payload)
    except Exception: return jsonify(payload)


@evaluation_bp.get("/api/evaluation")
@admin_required
def evaluation_api():
    return jsonify(evaluation_report())
