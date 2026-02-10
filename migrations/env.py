import os
import logging
from logging.config import fileConfig

from alembic import context
from flask import current_app
from sqlalchemy import engine_from_config, pool

from dotenv import load_dotenv

# ✅ carrega o .env da raiz (quando roda "flask db ...")
load_dotenv()

config = context.config

# logging do alembic
if config.config_file_name:
    fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")


def _escape_percent(s: str) -> str:
    # Alembic usa '%%' para escapar '%'
    return s.replace("%", "%%")


def get_engine_url() -> str:
    """Prioriza DATABASE_URL; fallback para o engine do Flask."""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        logger.info("Using DATABASE_URL from .env for Alembic migrations.")
        return _escape_percent(db_url)

    # fallback: pega do engine do Flask
    try:
        eng = current_app.extensions["migrate"].db.engine
    except Exception:
        eng = current_app.extensions["migrate"].db.get_engine()

    try:
        return _escape_percent(eng.url.render_as_string(hide_password=False))
    except AttributeError:
        return _escape_percent(str(eng.url))


# ✅ seta a URL no alembic.ini em runtime (funciona p/ offline e online)
config.set_main_option("sqlalchemy.url", get_engine_url())


# metadata do Flask-SQLAlchemy para autogenerate
target_db = current_app.extensions["migrate"].db


def get_metadata():
    if hasattr(target_db, "metadatas"):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        compare_type=True,  # ✅ aqui pode
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""

    # callback para evitar gerar revision vazia
    def process_revision_directives(ctx, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    conf_args = dict(current_app.extensions["migrate"].configure_args or {})
    conf_args.setdefault("process_revision_directives", process_revision_directives)

    # ✅ NÃO setar compare_type aqui manualmente se estiver em conf_args
    # (evita "multiple values for keyword argument 'compare_type'")
    # Se quiser garantir, você pode forçar:
    conf_args.setdefault("compare_type", True)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
