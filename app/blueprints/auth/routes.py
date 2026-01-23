from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ...extensions import db
from ...models import User, Sector
from .forms import LoginForm, RegisterForm

# ✅ Definição do Blueprint
bp = Blueprint("auth", __name__, url_prefix="/auth")

@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = LoginForm()

    if request.method == "POST":
        username = (request.form.get("matricula_or_email") or "").strip()
        password = request.form.get("password") or ""

        print("LOGIN DEBUG -> username:", repr(username), "pass_len:", len(password))

        if not username or not password:
            flash("Preencha matrícula/e-mail e senha.", "warning")
            return render_template("auth/login.html", form=form), 200

        user = User.query.filter(
            (db.func.lower(User.matricula) == username.lower()) |
            (db.func.lower(User.email) == username.lower())
        ).first()

        print("LOGIN DEBUG -> user:", user.id if user else None, "status:", getattr(user, "status", None))

        if not user or not user.check_password(password):
            flash("Matrícula/E-mail ou senha inválidos.", "danger")
            return render_template("auth/login.html", form=form), 200

        if user.status != "active":
            flash("Sua conta ainda não foi liberada pela gerência.", "warning")
            return render_template("auth/login.html", form=form), 200

        login_user(user, remember=True)
        next_url = request.args.get("next")
        print("LOGIN DEBUG -> logged in OK, redirect:", next_url or "dashboard.index")
        return redirect(next_url or url_for("dashboard.index")), 302

    return render_template("auth/login.html", form=form), 200


@bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    sectors = Sector.query.filter_by(active=True).order_by(Sector.name.asc()).all()
    form.setor.choices = [("", "— Selecione —")] + [(s.name, s.name) for s in sectors]

    if form.validate_on_submit():
        matricula = _next_matricula()
        email = (form.email.data or "").strip().lower() or None
        
        if email and User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "warning")
            return render_template("auth/register.html", form=form)

        user = User(
            matricula=matricula,
            nome=(form.nome.data or "").strip(),
            email=email,
            setor=form.setor.data or None,
            turno=form.turno.data or None,
            nascimento=form.nascimento.data,
            status="pending",
            role=form.role.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash(f"Solicitação enviada. Matrícula: {matricula}. Aguarde liberação.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

@bp.route("/users/pending", methods=["GET"])
@login_required
def users_pending():
    # Somente Manager ou Admin acessam pendências
    if current_user.role not in ['manager', 'admin']:
        flash("Acesso negado", "danger")
        return redirect(url_for("dashboard.index"))

    pending = User.query.filter_by(status="pending").order_by(User.created_at.desc()).all()
    return render_template("auth/pending.html", users=pending)

@bp.route("/users/<int:user_id>/approve", methods=["POST"])
@login_required
def approve_user(user_id: int):
    if current_user.role not in ['manager', 'admin']:
        return redirect(url_for("dashboard.index"))

    u = User.query.get_or_404(user_id)
    u.status = "active"
    db.session.commit()
    flash(f"Usuário liberado: {u.nome}", "success")
    return redirect(url_for("auth.users_pending"))

@bp.route("/users/<int:user_id>/block", methods=["POST"])
@login_required
def block_user(user_id: int):
    if current_user.role not in ['manager', 'admin']:
        return redirect(url_for("dashboard.index"))

    u = User.query.get_or_404(user_id)
    u.status = "blocked"
    db.session.commit()
    flash(f"Usuário bloqueado: {u.nome}", "warning")
    return redirect(url_for("auth.users_pending"))

# ✅ Rota de perfil - REDIRECIONA para settings
@bp.route("/profile", methods=["GET"])
@login_required
def profile():
    """Redireciona para a página de perfil em settings"""
    return redirect(url_for("settings.profile"))

# ✅ Rota de atualização de perfil - REDIRECIONA para settings
@bp.route("/profile/update", methods=["POST"])
@login_required
def profile_update():
    """Redireciona para a atualização de perfil em settings"""
    return redirect(url_for("settings.update_profile"), code=307)

# ✅ Helper function para gerar matrícula
def _next_matricula():
    """Gera uma matrícula sequencial simples"""
    last_user = User.query.order_by(User.id.desc()).first()
    if not last_user:
        return "ANA101"
    
    # Exemplo simples: ANA + ID + 100
    new_id = last_user.id + 101
    return f"ANA{new_id}"