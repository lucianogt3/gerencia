from flask import Blueprint, render_template
from flask_login import login_required
from ...utils.security import require_active

indicators_bp = Blueprint("indicators", __name__, url_prefix="/indicators")

@indicators_bp.route("/")
@login_required
@require_active
def index():
    return render_template("indicators/index.html")
