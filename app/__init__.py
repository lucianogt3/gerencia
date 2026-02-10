from flask import Flask, redirect, url_for
import os

from dotenv import load_dotenv
load_dotenv()

from .extensions import db, login_manager, csrf, migrate
from .commands import register_commands
from .models.user import User

from .blueprints.auth.routes import bp as auth_bp
from .blueprints.dashboard.routes import bp as dashboard_bp
from .blueprints.settings.routes import bp as settings_bp
from .blueprints.announcements.routes import bp as announcements_bp
from .blueprints.nursing_ui.routes import bp as nursing_ui_bp
from .blueprints.swaps.routes import bp as swaps_bp
from .blueprints.scales.routes import bp as scales_bp
from .blueprints.docs.routes import docs_bp
from .blueprints.indicators.routes import bp as indicators_bp
from .blueprints.medical_certificates.routes import bp as medical_certificates_bp


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None


def create_app():
    app = Flask(__name__)

    # ✅ 1) carrega config normal
    app.config.from_object("config.Config")

    # ✅ 2) SOBRESCREVE o banco se houver DATABASE_URL no .env
    # (isso garante Supabase mesmo que o config.py esteja errado)
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # --- EXTENSIONS ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    register_commands(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(nursing_ui_bp)
    app.register_blueprint(swaps_bp)
    app.register_blueprint(scales_bp)
    app.register_blueprint(medical_certificates_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(docs_bp)

    @app.route("/")
    def home():
        return redirect(url_for("auth.login"))

    return app
