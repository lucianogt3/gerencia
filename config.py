import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-desenvolvimento")

    SQLALCHEMY_DATABASE_URI = (os.getenv("DATABASE_URL") or "").strip()
    if not SQLALCHEMY_DATABASE_URI:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'instance' / 'app.db').as_posix()}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
