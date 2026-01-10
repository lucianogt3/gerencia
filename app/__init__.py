from __future__ import annotations

import os
from flask import Flask
from dotenv import load_dotenv

from .config import Config
from .extensions import db, login_manager, csrf


def create_app() -> Flask:
    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config())

    # 1) Garante instance/ existe (muito importante no Windows p/ sqlite e uploads)
    os.makedirs(app.instance_path, exist_ok=True)

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

    # register blueprints
    from .blueprints.main.routes import main_bp
    from .blueprints.auth.routes import auth_bp
    from .blueprints.docs.routes import docs_bp
    from .blueprints.scales.routes import scales_bp
    from .blueprints.indicators.routes import indicators_bp
    from .blueprints.swaps.routes import swaps_bp
    from .blueprints.sick_notes.routes import sick_notes_bp

    # NOVO: API da escala mensal/diária (se você criou o arquivo que eu te passei)
    # Se ainda não criou, comente essas 2 linhas por enquanto.
    from .blueprints.nursing import bp as nursing_api_bp


    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(docs_bp)
    app.register_blueprint(scales_bp)
    app.register_blueprint(indicators_bp)
    app.register_blueprint(swaps_bp)
    app.register_blueprint(sick_notes_bp)
    app.register_blueprint(nursing_api_bp)

    # create db tables
    with app.app_context():
        # garante que todos os models sejam importados/registrados no metadata
        from . import models  # noqa: F401
        db.create_all()

    # CLI commands
    from .seed import register_seed_command
    register_seed_command(app)

    return app
