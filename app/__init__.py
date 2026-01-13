from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, login_manager, csrf

# ✅ Labels PT-BR para roles (disponível em TODOS os templates)
ROLE_LABELS = {
    "staff": "Staff",
    "technician": "Técnico",
    "nurse": "Enfermeiro",
    "manager": "Gerência",
    "admin": "Admin",
}


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config())

    # 1) Garante instance/ existe (muito importante no Windows p/ sqlite e uploads)
    os.makedirs(app.instance_path, exist_ok=True)

    # ✅ 1.1) Força SQLite com caminho ABSOLUTO no instance/ (Windows-safe)
    db_path = Path(app.instance_path) / "app.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.as_posix()
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    # (debug opcional)
    print(">>> DB URI:", app.config.get("SQLALCHEMY_DATABASE_URI"))
    print(">>> INSTANCE:", app.instance_path)
    print(">>> CWD:", os.getcwd())

    # 2) Garante pasta de upload (com fallback seguro)
    upload_folder = app.config.get("UPLOAD_FOLDER") or os.path.join(app.instance_path, "uploads")
    app.config["UPLOAD_FOLDER"] = upload_folder
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # init extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # user loader
    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            return User.query.get(int(user_id))
        except Exception:
            return None

    login_manager.login_view = "auth.login"

    # ✅ Injeta variáveis globais nos templates (Jinja)
    @app.context_processor
    def inject_globals():
        return dict(ROLE_LABELS=ROLE_LABELS)

    # register blueprints
    from .blueprints.settings import bp as settings_bp
    from .blueprints.main.routes import main_bp
    from .blueprints.auth.routes import auth_bp
    from .blueprints.docs.routes import docs_bp
    from .blueprints.scales.routes import scales_bp
    from .blueprints.indicators.routes import indicators_bp
    from .blueprints.swaps.routes import swaps_bp
    from .blueprints.sick_notes.routes import sick_notes_bp
    from .blueprints.nursing_ui import bp as nursing_ui_bp
    from .blueprints.announcements.routes import bp as announcements_bp
    from .utils.jinja_helpers import month_name
    from .blueprints.nursing import bp as nursing_api_bp  # API escala mensal/diária

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(scales_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(swaps_bp)
    app.register_blueprint(sick_notes_bp)
    app.register_blueprint(nursing_api_bp)
    app.register_blueprint(nursing_ui_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(announcements_bp)

    app.jinja_env.globals["month_name"] = month_name

    # ✅ Importa models para registrar no metadata
    with app.app_context():
        from . import models  # noqa: F401
        # ❌ NÃO rode db.create_all() no boot (quebra no --debug no Windows)

    # ✅ CLI: init-db (criar tabelas manualmente 1 vez)
    @app.cli.command("init-db")
    def init_db_command():
        """Cria as tabelas do banco (SQLite) no instance/app.db."""
        from . import models  # noqa: F401

        with app.app_context():
            db.create_all()
        print("✅ Banco criado/atualizado com sucesso:", db_path)

    # ✅ CLI commands (SEED)
    from .seed import seed_command
    app.cli.add_command(seed_command)

    return app
