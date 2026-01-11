from flask import render_template

def register_error_handlers(app):
    @app.errorhandler(403)
    def forbidden(e):
        # use um template que você já tem, ou um simples
        return render_template("errors/403.html", title="Sem permissão"), 403
