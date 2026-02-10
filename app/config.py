import os
from pathlib import Path
from dotenv import load_dotenv

# 📌 Caminho absoluto da raiz do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# 📌 Caminho absoluto do .env
ENV_PATH = BASE_DIR / ".env"

# 🔥 Força o carregamento do .env
load_dotenv(dotenv_path=ENV_PATH, override=True)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-secreta-desenvolvimento")

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    if not SQLALCHEMY_DATABASE_URI:
        # fallback explícito
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'app.db'}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False
