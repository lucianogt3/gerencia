import os
import secrets
from werkzeug.utils import secure_filename
from flask import current_app

ALLOWED_DEFAULT = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".docx", ".xlsx"}

def save_upload(file_storage, subdir: str = "", allowed_exts=None) -> tuple[str, str]:
    """Salva upload e retorna (stored_filename, original_filename)."""
    if allowed_exts is None:
        allowed_exts = ALLOWED_DEFAULT

    original = file_storage.filename or "arquivo"
    filename = secure_filename(original)
    _, ext = os.path.splitext(filename.lower())
    if ext not in allowed_exts:
        raise ValueError(f"Tipo de arquivo não permitido: {ext}")

    token = secrets.token_hex(8)
    stored = f"{token}{ext}"

    folder = current_app.config["UPLOAD_FOLDER"]
    if subdir:
        folder = os.path.join(folder, subdir)
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, stored)
    file_storage.save(path)

    return stored, original
