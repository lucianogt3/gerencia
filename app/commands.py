from .seed import seed_command

def register_commands(app):
    """
    Registra comandos de linha de comando (CLI) personalizados.
    Exemplo: flask seed
    """
    app.cli.add_command(seed_command)