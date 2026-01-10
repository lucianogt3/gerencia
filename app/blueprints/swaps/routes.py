from flask import Blueprint, render_template
from flask_login import login_required
from ...utils.security import require_active

swaps_bp = Blueprint("swaps", __name__, url_prefix="/swaps")

@swaps_bp.route("/")
@login_required
@require_active
def index():
    return render_template("swaps/index.html")
