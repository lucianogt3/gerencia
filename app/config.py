import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads")
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    DB_PATH = os.path.join(INSTANCE_DIR, "app.db")

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///" + DB_PATH.replace("\\", "/"),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
