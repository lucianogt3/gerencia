import os

class Config:
    # Pasta raiz do projeto
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Chave de seguranca
    SECRET_KEY = "chave-secreta-desenvolvimento"

    # Pasta instance para o banco de dados
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    if not os.path.exists(INSTANCE_DIR):
        os.makedirs(INSTANCE_DIR)
        
    # Caminho do banco SQLite
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "app.db").replace("\\", "/")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Pasta de Uploads
    UPLOAD_FOLDER = os.path.join(INSTANCE_DIR, "uploads")
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
