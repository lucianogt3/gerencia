import os

class Config:
    # Pega a pasta onde este arquivo está (Raiz do projeto)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Chave de segurança
    SECRET_KEY = "chave-secreta-desenvolvimento"

    # Cria a pasta 'instance' dentro do projeto
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    
    # Define o caminho do banco de dados (app.db)
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(INSTANCE_DIR, "app.db").replace("\\", "/")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False