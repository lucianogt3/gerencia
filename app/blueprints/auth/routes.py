from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ...extensions import db
from ...models.user import User
from ...utils.security import require_roles
from .forms import LoginForm, RegisterForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated and current_user.status == "active":
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        key = (form.matricula_or_email.data or "").strip().lower()
        user = User.query.filter((User.matricula == key) | (User.email == key)).first()
        if not user or not user.check_password(form.password.data):
            flash("Login inválido.", "danger")
            return render_template("auth/login.html", form=form)

        login_user(user)
        if user.status != "active":
            return redirect(url_for("main.root"))
        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", form=form)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        matricula = (form.matricula.data or "").strip()
        if User.query.filter_by(matricula=matricula).first():
            flash("Matrícula já cadastrada.", "warning")
            return render_template("auth/register.html", form=form)

        email = (form.email.data or "").strip().lower() or None
        if email and User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "warning")
            return render_template("auth/register.html", form=form)

        user = User(
            matricula=matricula,
            nome=form.nome.data.strip(),
            email=email,
            setor=(form.setor.data or "").strip() or None,
            turno=form.turno.data or None,
            nascimento=form.nascimento.data,
            status="pending",
            role="staff",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash("Solicitação enviada. Aguarde liberação da gerência.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))

# Gerência aprova usuários pendentes
@auth_bp.route("/users/pending", methods=["GET", "POST"])
@login_required
@require_roles("manager", "admin")
def users_pending():
    pending = User.query.filter_by(status="pending").order_by(User.created_at.desc()).all()
    return render_template("auth/users_pending.html", pending=pending)

@auth_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@login_required
@require_roles("manager", "admin")
def approve_user(user_id: int):
    u = User.query.get_or_404(user_id)
    u.status = "active"
    db.session.commit()
    flash(f"Usuário liberado: {u.nome} ({u.matricula})", "success")
    return redirect(url_for("auth.users_pending"))

@auth_bp.route("/users/<int:user_id>/block", methods=["POST"])
@login_required
@require_roles("manager", "admin")
def block_user(user_id: int):
    u = User.query.get_or_404(user_id)
    u.status = "blocked"
    db.session.commit()
    flash(f"Usuário bloqueado: {u.nome} ({u.matricula})", "warning")
    return redirect(url_for("auth.users_pending"))
