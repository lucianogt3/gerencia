import os, textwrap, zipfile, json, re, datetime, pathlib, shutil, hashlib
base = "/mnt/data/nurse_manager_portal_patch"
if os.path.exists(base):
    shutil.rmtree(base)
os.makedirs(base, exist_ok=True)

def w(path, content):
    fp = os.path.join(base, path)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(content)

# Core backend files
w("wsgi.py", textwrap.dedent("""\
    from app import create_app

    app = create_app()

    if __name__ == "__main__":
        app.run()
"""))

w("manage.py", textwrap.dedent("""\
    from app import create_app

    app = create_app()

    if __name__ == "__main__":
        # Convenience entrypoint: python manage.py
        app.run(debug=True)
"""))

w("requirements.txt", textwrap.dedent("""\
    Flask==3.0.3
    Flask-SQLAlchemy==3.1.1
    Flask-Login==0.6.3
    python-dotenv==1.0.1
    Werkzeug==3.0.3
"""))

w("README_UPDATE.md", textwrap.dedent("""\
    # Nurse Manager Portal — Patch (Escala, Folgas, Atestados, Alertas e Feedback)

    Este ZIP é um "patch" com arquivos **novos** e arquivos **atualizados** (substituir/overwrite),
    trazendo:

    - Escala mensal por setor (gerência)
    - Escala diária (enfermeiro) baseada na escala mensal
    - Substituição / remanejamento / extra / folga (com regras)
    - Registro de faltas e atestados (com aprovação do gestor)
    - Alertas de folga (24h antes)
    - Módulo de Solicitação / Elogio / Reclamação (Feedback)

    ## Como aplicar (Windows / PowerShell)

    1) **Backup do projeto atual**
       - Copie a pasta do projeto para um backup, ex:
         `C:\\Users\\LUCIANO\\Desktop\\nurse_manager_portal_backup`

    2) **Extrair este ZIP por cima do projeto**
       - Extraia o conteúdo deste ZIP dentro de:
         `C:\\Users\\LUCIANO\\Desktop\\nurse_manager_portal\\`
       - Permita substituir arquivos quando solicitado.

    3) **Criar e ativar venv (se não existir)**
       - Dentro da pasta do projeto:
         - `python -m venv .venv`
         - `.\.venv\\Scripts\\Activate.ps1`

    4) **Instalar dependências**
       - `pip install -r requirements.txt`

    5) **Criar pastas instance/uploads**
       - `mkdir .\\instance -Force`
       - `mkdir .\\instance\\uploads -Force`

    6) **Rodar seed (cria admin + dados exemplo)**
       - `python -m flask --app wsgi seed`

    7) **Rodar o servidor**
       - `python -m flask --app wsgi run --debug`
       - Abra: http://127.0.0.1:5000

    ## Login seed
    - Email: admin@portal.local
    - Senha: admin123

    > Troque a senha depois no banco / tela de gestão (fica como pendência para próxima etapa).

    ## Observação
    - O banco padrão é SQLite em `instance/app.db`.
    - O upload fica em `instance/uploads`.

"""))

# .env example
w(".env.example", textwrap.dedent("""\
    # Copie para .env se quiser
    FLASK_ENV=development
    SECRET_KEY=dev-secret-change-me

    # Se quiser apontar outro DB:
    # SQLALCHEMY_DATABASE_URI=sqlite:///instance/app.db
"""))

w(".gitignore", textwrap.dedent("""\
    .venv/
    __pycache__/
    *.pyc
    instance/app.db
    instance/uploads/
    .env
"""))

# app package
w("app/__init__.py", textwrap.dedent("""\
    import os
    from flask import Flask
    from dotenv import load_dotenv

    from .config import Config
    from .extensions import db, login_manager
    from .auth import auth_bp
    from .main import main_bp
    from .manager import manager_bp
    from .nurse import nurse_bp
    from .feedback import feedback_bp

    def create_app():
        load_dotenv()

        app = Flask(__name__, instance_relative_config=True)

        # Base config
        app.config.from_object(Config())

        # Guarantee instance path exists
        os.makedirs(app.instance_path, exist_ok=True)

        # Upload folder
        upload_folder = app.config.get("UPLOAD_FOLDER")
        if not upload_folder:
            upload_folder = os.path.join(app.instance_path, "uploads")
            app.config["UPLOAD_FOLDER"] = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

        # Database init
        db.init_app(app)
        login_manager.init_app(app)

        # Blueprints
        app.register_blueprint(auth_bp)
        app.register_blueprint(main_bp)
        app.register_blueprint(manager_bp)
        app.register_blueprint(nurse_bp)
        app.register_blueprint(feedback_bp)

        # Create tables (simple setup)
        with app.app_context():
            from . import models  # noqa: F401
            db.create_all()

        # CLI commands
        from .seed import seed_command
        app.cli.add_command(seed_command)

        return app
"""))

w("app/config.py", textwrap.dedent("""\
    import os

    class Config:
        SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
        SQLALCHEMY_TRACK_MODIFICATIONS = False

        # Use absolute path to avoid sqlite "unable to open database file"
        # Default: <project>/instance/app.db via instance_relative_config.
        SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///instance/app.db")

        # Uploads inside instance/
        UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", None)

        # Alerts
        ALERT_FOLGA_HOURS = int(os.getenv("ALERT_FOLGA_HOURS", "24"))
"""))

w("app/extensions.py", textwrap.dedent("""\
    from flask_sqlalchemy import SQLAlchemy
    from flask_login import LoginManager

    db = SQLAlchemy()
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
"""))

# Models
w("app/models.py", textwrap.dedent("""\
    from __future__ import annotations
    from datetime import datetime, date
    from enum import Enum

    from flask_login import UserMixin
    from werkzeug.security import generate_password_hash, check_password_hash

    from .extensions import db
    from .extensions import login_manager


    class Role(str, Enum):
        ADMIN = "ADMIN"
        MANAGER = "MANAGER"
        NURSE = "NURSE"


    class FeedbackType(str, Enum):
        SOLICITACAO = "SOLICITACAO"
        ELOGIO = "ELOGIO"
        RECLAMACAO = "RECLAMACAO"


    class AbsenceType(str, Enum):
        FALTA_NJ = "FALTA_NJ"        # falta não justificada
        FALTA_J = "FALTA_J"          # falta justificada manual
        ATESTADO = "ATESTADO"


    class CoverageType(str, Enum):
        REMANEJO = "REMANEJO"
        EXTRA = "EXTRA"
        FOLGA = "FOLGA"


    class ApprovalStatus(str, Enum):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"


    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), nullable=False)
        email = db.Column(db.String(120), unique=True, nullable=False, index=True)
        password_hash = db.Column(db.String(255), nullable=False)
        role = db.Column(db.String(20), nullable=False, default=Role.NURSE.value)

        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def set_password(self, pw: str) -> None:
            self.password_hash = generate_password_hash(pw)

        def check_password(self, pw: str) -> bool:
            return check_password_hash(self.password_hash, pw)

        def is_manager(self) -> bool:
            return self.role in (Role.MANAGER.value, Role.ADMIN.value)

        def is_admin(self) -> bool:
            return self.role == Role.ADMIN.value


    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))


    class Sector(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(120), unique=True, nullable=False)

        created_at = db.Column(db.DateTime, default=datetime.utcnow)


    class Professional(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(160), nullable=False, index=True)
        category = db.Column(db.String(40), nullable=False)  # ENF, TEC, MED, FISIO etc.
        active = db.Column(db.Boolean, default=True)

        created_at = db.Column(db.DateTime, default=datetime.utcnow)


    class MonthlySchedule(db.Model):
        \"\"\"Escala mensal inserida pela gerência.\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"), nullable=False)
        year = db.Column(db.Integer, nullable=False)
        month = db.Column(db.Integer, nullable=False)

        created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        sector = db.relationship("Sector")
        creator = db.relationship("User")


    class MonthlyAssignment(db.Model):
        \"\"\"Linha (um profissional) na escala mensal.\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        schedule_id = db.Column(db.Integer, db.ForeignKey("monthly_schedule.id"), nullable=False)
        professional_id = db.Column(db.Integer, db.ForeignKey("professional.id"), nullable=False)

        # JSON simples de turnos por dia: {"1":"D","2":"N","3":"F",...}
        days_json = db.Column(db.Text, nullable=False, default="{}")

        schedule = db.relationship("MonthlySchedule", backref="assignments")
        professional = db.relationship("Professional")


    class DailyShift(db.Model):
        \"\"\"Plantão diário montado pelo enfermeiro, baseado no mensal.\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"), nullable=False)
        shift_date = db.Column(db.Date, nullable=False)
        turn = db.Column(db.String(10), nullable=False)  # D/N/12x36 etc.

        created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        sector = db.relationship("Sector")
        creator = db.relationship("User")

        __table_args__ = (
            db.UniqueConstraint("sector_id", "shift_date", "turn", name="uq_dailyshift_sector_date_turn"),
        )


    class DailyPosition(db.Model):
        \"\"\"Posições do dia (Enf, Tec1..Tec5 etc).\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        daily_shift_id = db.Column(db.Integer, db.ForeignKey("daily_shift.id"), nullable=False)
        position_key = db.Column(db.String(40), nullable=False)  # ENF, TEC_1, TEC_2...
        scheduled_professional_id = db.Column(db.Integer, db.ForeignKey("professional.id"), nullable=True)
        actual_professional_id = db.Column(db.Integer, db.ForeignKey("professional.id"), nullable=True)

        absence_type = db.Column(db.String(20), nullable=True)  # AbsenceType
        absence_note = db.Column(db.String(255), nullable=True)

        daily_shift = db.relationship("DailyShift", backref="positions")
        scheduled_professional = db.relationship("Professional", foreign_keys=[scheduled_professional_id])
        actual_professional = db.relationship("Professional", foreign_keys=[actual_professional_id])


    class CoverageEvent(db.Model):
        \"\"\"Substituição / remanejo / extra / folga ligada a uma posição diária.\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        daily_position_id = db.Column(db.Integer, db.ForeignKey("daily_position.id"), nullable=False)

        coverage_type = db.Column(db.String(20), nullable=False)  # CoverageType
        origin_sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"), nullable=True)

        # Para FOLGA
        off_date = db.Column(db.Date, nullable=True)

        status = db.Column(db.String(20), nullable=False, default=ApprovalStatus.PENDING.value)

        created_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        position = db.relationship("DailyPosition", backref="coverage_events")
        origin_sector = db.relationship("Sector")
        creator = db.relationship("User")


    class CertificateRequest(db.Model):
        \"\"\"Atestado enviado pelo colaborador (ou registrado pelo enfermeiro) e aprovado pela gerência.\"\"\"
        id = db.Column(db.Integer, primary_key=True)
        professional_id = db.Column(db.Integer, db.ForeignKey("professional.id"), nullable=False)

        start_date = db.Column(db.Date, nullable=False)
        end_date = db.Column(db.Date, nullable=False)

        file_path = db.Column(db.String(255), nullable=True)  # opcional
        status = db.Column(db.String(20), nullable=False, default=ApprovalStatus.PENDING.value)

        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        approved_at = db.Column(db.DateTime, nullable=True)
        reviewed_by = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)

        professional = db.relationship("Professional")
        reviewer = db.relationship("User")


    class FeedbackTicket(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        ticket_type = db.Column(db.String(20), nullable=False)  # FeedbackType
        subject = db.Column(db.String(160), nullable=False)
        message = db.Column(db.Text, nullable=False)

        sector_id = db.Column(db.Integer, db.ForeignKey("sector.id"), nullable=True)
        created_by_name = db.Column(db.String(160), nullable=True)  # opcional (público)
        created_by_email = db.Column(db.String(160), nullable=True)

        status = db.Column(db.String(20), nullable=False, default="OPEN")  # OPEN/CLOSED
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        sector = db.relationship("Sector")


    class Alert(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        alert_type = db.Column(db.String(40), nullable=False)  # FOLGA_24H
        scheduled_for = db.Column(db.DateTime, nullable=False)
        sent_at = db.Column(db.DateTime, nullable=True)

        manager_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
        payload_json = db.Column(db.Text, nullable=False, default="{}")

        manager = db.relationship("User")
"""))

# Auth blueprint
w("app/auth.py", textwrap.dedent("""\
    from flask import Blueprint, render_template, request, redirect, url_for, flash
    from flask_login import login_user, logout_user, login_required, current_user

    from .models import User
    from .extensions import db

    auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

    @auth_bp.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("main.home"))

        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            senha = request.form.get("senha") or ""
            user = User.query.filter_by(email=email).first()
            if not user or not user.check_password(senha):
                flash("Login inválido.", "danger")
                return render_template("login.html")
            login_user(user)
            return redirect(url_for("main.home"))

        return render_template("login.html")

    @auth_bp.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("auth.login"))
"""))

# Main + role router
w("app/main.py", textwrap.dedent("""\
    from flask import Blueprint, redirect, url_for
    from flask_login import login_required, current_user

    main_bp = Blueprint("main", __name__)

    @main_bp.route("/")
    @login_required
    def home():
        # Route user by role
        if current_user.is_manager():
            return redirect(url_for("manager.dashboard"))
        return redirect(url_for("nurse.dashboard"))
"""))

# Manager blueprint
w("app/manager.py", textwrap.dedent("""\
    from datetime import date, datetime, timedelta
    import json

    from flask import Blueprint, render_template, request, redirect, url_for, flash
    from flask_login import login_required, current_user

    from .extensions import db
    from .models import (
        Sector, Professional,
        MonthlySchedule, MonthlyAssignment,
        CertificateRequest, FeedbackTicket,
        CoverageEvent, ApprovalStatus, CoverageType, Alert
    )

    manager_bp = Blueprint("manager", __name__, url_prefix="/manager")


    def manager_required():
        if not current_user.is_manager():
            flash("Acesso restrito à gerência.", "danger")
            return False
        return True


    @manager_bp.route("/dashboard")
    @login_required
    def dashboard():
        if not manager_required():
            return redirect(url_for("main.home"))

        today = date.today()
        month_start = date(today.year, today.month, 1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)

        # Extras/Folgas pendentes no mês
        extras = CoverageEvent.query.filter(
            CoverageEvent.coverage_type == CoverageType.EXTRA.value,
            CoverageEvent.created_at >= datetime(today.year, today.month, 1)
        ).count()

        folgas_abertas = CoverageEvent.query.filter(
            CoverageEvent.coverage_type == CoverageType.FOLGA.value,
            CoverageEvent.status.in_([ApprovalStatus.PENDING.value, ApprovalStatus.APPROVED.value]),
            CoverageEvent.off_date != None
        ).count()

        atestados_pendentes = CertificateRequest.query.filter_by(status=ApprovalStatus.PENDING.value).count()
        tickets_abertos = FeedbackTicket.query.filter_by(status="OPEN").count()

        # Alerts 24h (simplificado: alertas ainda não enviados e scheduled_for <= agora)
        alerts_due = Alert.query.filter(Alert.sent_at == None, Alert.scheduled_for <= datetime.utcnow()).all()

        return render_template(
            "manager/dashboard.html",
            extras=extras,
            folgas_abertas=folgas_abertas,
            atestados_pendentes=atestados_pendentes,
            tickets_abertos=tickets_abertos,
            alerts_due=alerts_due
        )


    @manager_bp.route("/monthly", methods=["GET", "POST"])
    @login_required
    def monthly_schedule():
        if not manager_required():
            return redirect(url_for("main.home"))

        sectors = Sector.query.order_by(Sector.name).all()
        professionals = Professional.query.filter_by(active=True).order_by(Professional.category, Professional.name).all()

        if request.method == "POST":
            sector_id = int(request.form.get("sector_id"))
            year = int(request.form.get("year"))
            month = int(request.form.get("month"))

            sched = MonthlySchedule(sector_id=sector_id, year=year, month=month, created_by=current_user.id)
            db.session.add(sched)
            db.session.commit()

            # assignments will be edited in a simple second screen
            flash("Escala mensal criada. Agora edite os profissionais e turnos.", "success")
            return redirect(url_for("manager.monthly_edit", schedule_id=sched.id))

        return render_template("manager/monthly_create.html", sectors=sectors, professionals=professionals)


    @manager_bp.route("/monthly/<int:schedule_id>/edit", methods=["GET", "POST"])
    @login_required
    def monthly_edit(schedule_id: int):
        if not manager_required():
            return redirect(url_for("main.home"))

        sched = MonthlySchedule.query.get_or_404(schedule_id)
        sector = sched.sector
        professionals = Professional.query.filter_by(active=True).order_by(Professional.category, Professional.name).all()

        if request.method == "POST":
            # Add professional to schedule
            prof_id = int(request.form.get("professional_id"))
            exists = MonthlyAssignment.query.filter_by(schedule_id=sched.id, professional_id=prof_id).first()
            if not exists:
                db.session.add(MonthlyAssignment(schedule_id=sched.id, professional_id=prof_id, days_json="{}"))
                db.session.commit()
                flash("Profissional adicionado.", "success")
            return redirect(url_for("manager.monthly_edit", schedule_id=sched.id))

        return render_template("manager/monthly_edit.html", sched=sched, sector=sector, professionals=professionals)


    @manager_bp.route("/monthly/<int:schedule_id>/save_days", methods=["POST"])
    @login_required
    def monthly_save_days(schedule_id: int):
        if not manager_required():
            return redirect(url_for("main.home"))

        sched = MonthlySchedule.query.get_or_404(schedule_id)
        # Expect fields: days_json_<assignment_id>
        for a in sched.assignments:
            key = f"days_json_{a.id}"
            if key in request.form:
                a.days_json = request.form.get(key) or "{}"
        db.session.commit()
        flash("Escala mensal atualizada.", "success")
        return redirect(url_for("manager.monthly_edit", schedule_id=schedule_id))


    @manager_bp.route("/folgas", methods=["GET", "POST"])
    @login_required
    def folgas():
        if not manager_required():
            return redirect(url_for("main.home"))

        if request.method == "POST":
            # Ajustar data da folga (autonomia do gerente)
            event_id = int(request.form.get("event_id"))
            new_date = request.form.get("off_date")
            ev = CoverageEvent.query.get_or_404(event_id)
            if new_date:
                ev.off_date = date.fromisoformat(new_date)
                db.session.commit()
                flash("Data da folga ajustada.", "success")
        folgas = CoverageEvent.query.filter(CoverageEvent.coverage_type == CoverageType.FOLGA.value).order_by(CoverageEvent.off_date.desc()).all()
        return render_template("manager/folgas.html", folgas=folgas)


    @manager_bp.route("/atestados", methods=["GET", "POST"])
    @login_required
    def atestados():
        if not manager_required():
            return redirect(url_for("main.home"))

        if request.method == "POST":
            req_id = int(request.form.get("req_id"))
            action = request.form.get("action")
            req = CertificateRequest.query.get_or_404(req_id)
            if action == "approve":
                req.status = ApprovalStatus.APPROVED.value
                req.reviewed_by = current_user.id
                req.approved_at = datetime.utcnow()
            elif action == "reject":
                req.status = ApprovalStatus.REJECTED.value
                req.reviewed_by = current_user.id
                req.approved_at = datetime.utcnow()
            db.session.commit()
            flash("Atestado atualizado.", "success")

        pendentes = CertificateRequest.query.order_by(CertificateRequest.created_at.desc()).all()
        return render_template("manager/atestados.html", atestados=pendentes)


    @manager_bp.route("/tickets", methods=["GET", "POST"])
    @login_required
    def tickets():
        if not manager_required():
            return redirect(url_for("main.home"))

        if request.method == "POST":
            ticket_id = int(request.form.get("ticket_id"))
            action = request.form.get("action")
            t = FeedbackTicket.query.get_or_404(ticket_id)
            if action == "close":
                t.status = "CLOSED"
                db.session.commit()
                flash("Ticket encerrado.", "success")
        tickets = FeedbackTicket.query.order_by(FeedbackTicket.created_at.desc()).all()
        return render_template("manager/tickets.html", tickets=tickets)
"""))

# Nurse blueprint
w("app/nurse.py", textwrap.dedent("""\
    from datetime import date
    import json

    from flask import Blueprint, render_template, request, redirect, url_for, flash
    from flask_login import login_required, current_user

    from .extensions import db
    from .models import (
        Sector, Professional,
        MonthlySchedule, MonthlyAssignment,
        DailyShift, DailyPosition,
        CoverageEvent, CoverageType, ApprovalStatus,
        CertificateRequest
    )

    nurse_bp = Blueprint("nurse", __name__, url_prefix="/nurse")


    @nurse_bp.route("/dashboard")
    @login_required
    def dashboard():
        sectors = Sector.query.order_by(Sector.name).all()
        return render_template("nurse/dashboard.html", sectors=sectors)


    def _get_monthly_schedule(sector_id: int, d: date):
        return MonthlySchedule.query.filter_by(sector_id=sector_id, year=d.year, month=d.month).order_by(MonthlySchedule.id.desc()).first()


    @nurse_bp.route("/daily", methods=["GET", "POST"])
    @login_required
    def daily():
        sectors = Sector.query.order_by(Sector.name).all()

        # Default selections
        sector_id = int(request.values.get("sector_id") or (sectors[0].id if sectors else 0))
        shift_date = request.values.get("shift_date") or date.today().isoformat()
        turn = request.values.get("turn") or "D"

        if not sector_id:
            flash("Cadastre um setor primeiro (seed já cria UTI 1/2/3).", "warning")
            return render_template("nurse/daily.html", sectors=sectors, sector_id=0, shift_date=shift_date, turn=turn, rows=[])

        d = date.fromisoformat(shift_date)

        daily_shift = DailyShift.query.filter_by(sector_id=sector_id, shift_date=d, turn=turn).first()
        if not daily_shift:
            daily_shift = DailyShift(sector_id=sector_id, shift_date=d, turn=turn, created_by=current_user.id)
            db.session.add(daily_shift)
            db.session.commit()
            # create default positions
            default_positions = ["ENF", "TEC_1", "TEC_2", "TEC_3", "TEC_4", "TEC_5"]
            for pk in default_positions:
                db.session.add(DailyPosition(daily_shift_id=daily_shift.id, position_key=pk))
            db.session.commit()

        # Build from monthly schedule (for suggestions)
        sched = _get_monthly_schedule(sector_id, d)
        suggested = {}
        if sched:
            day = str(d.day)
            for a in sched.assignments:
                days = json.loads(a.days_json or "{}")
                if days.get(day) == turn:
                    suggested.setdefault(a.professional.category, []).append(a.professional)

        professionals = Professional.query.filter_by(active=True).order_by(Professional.category, Professional.name).all()

        if request.method == "POST":
            # Save positions
            for pos in daily_shift.positions:
                sched_key = f"scheduled_{pos.id}"
                actual_key = f"actual_{pos.id}"
                absence_key = f"absence_{pos.id}"
                note_key = f"absence_note_{pos.id}"

                pos.scheduled_professional_id = int(request.form.get(sched_key) or 0) or None
                pos.actual_professional_id = int(request.form.get(actual_key) or 0) or None

                abs_val = request.form.get(absence_key) or ""
                pos.absence_type = abs_val or None
                pos.absence_note = (request.form.get(note_key) or "").strip() or None

            db.session.commit()
            flash("Escala do dia salva.", "success")
            return redirect(url_for("nurse.daily", sector_id=sector_id, shift_date=shift_date, turn=turn))

        return render_template(
            "nurse/daily.html",
            sectors=sectors,
            sector_id=sector_id,
            shift_date=shift_date,
            turn=turn,
            daily_shift=daily_shift,
            professionals=professionals,
            suggested=suggested
        )


    @nurse_bp.route("/coverage/add", methods=["POST"])
    @login_required
    def add_coverage():
        \"\"\"Registrar remanejo/extra/folga quando o profissional não está escalado.\"\"\"
        pos_id = int(request.form.get("pos_id"))
        coverage_type = request.form.get("coverage_type")
        origin_sector_id = request.form.get("origin_sector_id")
        off_date = request.form.get("off_date")

        pos = DailyPosition.query.get_or_404(pos_id)

        ev = CoverageEvent(
            daily_position_id=pos.id,
            coverage_type=coverage_type,
            origin_sector_id=int(origin_sector_id) if origin_sector_id else None,
            off_date=date.fromisoformat(off_date) if off_date else None,
            status=ApprovalStatus.PENDING.value,
            created_by=current_user.id,
        )
        db.session.add(ev)
        db.session.commit()

        flash("Cobertura registrada (pendente para gerência quando aplicável).", "success")
        return redirect(url_for("nurse.daily", sector_id=pos.daily_shift.sector_id, shift_date=pos.daily_shift.shift_date.isoformat(), turn=pos.daily_shift.turn))


    @nurse_bp.route("/atestados/enviar", methods=["GET", "POST"])
    @login_required
    def enviar_atestado():
        professionals = Professional.query.filter_by(active=True).order_by(Professional.name).all()

        if request.method == "POST":
            professional_id = int(request.form.get("professional_id"))
            start_date = date.fromisoformat(request.form.get("start_date"))
            end_date = date.fromisoformat(request.form.get("end_date"))

            req = CertificateRequest(
                professional_id=professional_id,
                start_date=start_date,
                end_date=end_date,
                status=ApprovalStatus.PENDING.value,
            )
            db.session.add(req)
            db.session.commit()
            flash("Atestado enviado para aprovação.", "success")
            return redirect(url_for("nurse.dashboard"))

        return render_template("nurse/enviar_atestado.html", professionals=professionals)
"""))

# Feedback blueprint (public + inside)
w("app/feedback.py", textwrap.dedent("""\
    from flask import Blueprint, render_template, request, redirect, url_for, flash
    from .extensions import db
    from .models import Sector, FeedbackTicket, FeedbackType

    feedback_bp = Blueprint("feedback", __name__, url_prefix="/feedback")

    @feedback_bp.route("/novo", methods=["GET", "POST"])
    def novo():
        sectors = Sector.query.order_by(Sector.name).all()
        if request.method == "POST":
            ticket_type = request.form.get("ticket_type")
            subject = (request.form.get("subject") or "").strip()
            message = (request.form.get("message") or "").strip()
            sector_id = request.form.get("sector_id") or None
            created_by_name = (request.form.get("name") or "").strip() or None
            created_by_email = (request.form.get("email") or "").strip() or None

            if not subject or not message:
                flash("Assunto e mensagem são obrigatórios.", "danger")
                return render_template("feedback/novo.html", sectors=sectors)

            t = FeedbackTicket(
                ticket_type=ticket_type or FeedbackType.SOLICITACAO.value,
                subject=subject,
                message=message,
                sector_id=int(sector_id) if sector_id else None,
                created_by_name=created_by_name,
                created_by_email=created_by_email,
                status="OPEN",
            )
            db.session.add(t)
            db.session.commit()
            flash("Enviado! Obrigado pelo contato. A gerência vai avaliar.", "success")
            return redirect(url_for("feedback.novo"))

        return render_template("feedback/novo.html", sectors=sectors)
"""))

# Seed command
w("app/seed.py", textwrap.dedent("""\
    from datetime import date
    import click

    from .extensions import db
    from .models import User, Role, Sector, Professional


    @click.command("seed")
    def seed_command():
        \"\"\"Seed básico: admin, setores e alguns profissionais.\"\"\"
        # Admin
        admin = User.query.filter_by(email="admin@portal.local").first()
        if not admin:
            admin = User(name="Admin", email="admin@portal.local", role=Role.ADMIN.value)
            admin.set_password("admin123")
            db.session.add(admin)

        # Sectors
        for name in ["UTI 1", "UTI 2", "UTI 3"]:
            if not Sector.query.filter_by(name=name).first():
                db.session.add(Sector(name=name))

        db.session.commit()

        # Professionals (exemplo)
        sample = [
            ("João Enfermeiro", "ENF"),
            ("Maria Enfermeira", "ENF"),
            ("Tec 1", "TEC"),
            ("Tec 2", "TEC"),
            ("Tec 3", "TEC"),
            ("Tec 4", "TEC"),
            ("Tec 5", "TEC"),
            ("Tec 6", "TEC"),
            ("Fisio 1", "FISIO"),
        ]
        for name, cat in sample:
            if not Professional.query.filter_by(name=name, category=cat).first():
                db.session.add(Professional(name=name, category=cat, active=True))

        db.session.commit()

        click.echo("Seed concluído: admin@portal.local / admin123, setores UTI 1/2/3 e profissionais exemplo.")
"""))

# Templates (Bootstrap 5)
layout = """\
{% set title = title or "Nurse Manager Portal" %}
<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #0b1220; }
    .app-shell { min-height: 100vh; }
    .sidebar { background: #0f1a33; border-right: 1px solid rgba(255,255,255,.08); }
    .card { border: 1px solid rgba(255,255,255,.08); background: #0f1a33; color: #e8eefc; }
    .muted { color: rgba(232,238,252,.72); }
    .table { color: #e8eefc; }
    .table thead th { color: rgba(232,238,252,.8); }
    .nav-link { color: rgba(232,238,252,.8); }
    .nav-link.active, .nav-link:hover { color: #fff; background: rgba(255,255,255,.06); border-radius: 10px; }
    .badge-soft { background: rgba(255,255,255,.08); color: #e8eefc; border: 1px solid rgba(255,255,255,.10); }
    .btn-soft { background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.10); color: #fff; }
    .btn-soft:hover { background: rgba(255,255,255,.12); }
    .hero { border: 1px solid rgba(255,255,255,.08); background: linear-gradient(180deg, rgba(99,102,241,.16), rgba(15,26,51,.5)); }
    a { text-decoration: none; }
  </style>
</head>
<body>
<div class="app-shell d-flex">
  <aside class="sidebar p-3" style="width: 280px;">
    <div class="mb-3">
      <div class="fw-bold text-white" style="font-size: 1.1rem;">Passagem de Plantão</div>
      <div class="muted" style="font-size: .9rem;">Nurse Manager Portal</div>
    </div>
    {% if current_user.is_authenticated %}
    <div class="mb-3">
      <div class="muted" style="font-size: .85rem;">Logado:</div>
      <div class="text-white">{{ current_user.name }}</div>
      <span class="badge badge-soft mt-1">{{ current_user.role }}</span>
    </div>
    {% endif %}
    <nav class="nav flex-column gap-1">
      {% block sidebar %}{% endblock %}
      {% if current_user.is_authenticated %}
      <a class="nav-link" href="{{ url_for('auth.logout') }}">Sair</a>
      {% endif %}
    </nav>
    <hr class="border-light opacity-10" />
    <a class="nav-link" href="{{ url_for('feedback.novo') }}">📨 Enviar solicitação/elogio/reclamação</a>
  </aside>

  <main class="flex-fill p-4">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        {% for cat, msg in messages %}
          <div class="alert alert-{{ cat }} mb-3">{{ msg }}</div>
        {% endfor %}
      {% endif %}
    {% endwith %}

    {% block content %}{% endblock %}
  </main>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
{% block scripts %}{% endblock %}
</body>
</html>
"""
w("app/templates/layout.html", layout)

w("app/templates/login.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% block sidebar %}
  <a class="nav-link active" href="{{ url_for('auth.login') }}">Login</a>
{% endblock %}
{% block content %}
  <div class="container" style="max-width: 420px;">
    <div class="card p-4">
      <h4 class="mb-2">Entrar</h4>
      <div class="muted mb-3">Acesse com seu usuário e senha.</div>

      <form method="post">
        <div class="mb-3">
          <label class="form-label">Email</label>
          <input class="form-control" name="email" type="email" required />
        </div>
        <div class="mb-3">
          <label class="form-label">Senha</label>
          <input class="form-control" name="senha" type="password" required />
        </div>
        <button class="btn btn-primary w-100">Entrar</button>
      </form>

      <hr class="border-light opacity-10 my-3" />
      <div class="muted" style="font-size: .9rem;">
        Ou envie um contato para a gerência:
        <a href="{{ url_for('feedback.novo') }}">abrir formulário</a>
      </div>
    </div>
  </div>
{% endblock %}
"""))

# Manager templates
w("app/templates/manager/dashboard.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Painel da Gerência" %}
{% block sidebar %}
  <a class="nav-link active" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link" href="{{ url_for('manager.tickets') }}">💬 Tickets (elogio/reclamação)</a>
{% endblock %}

{% block content %}
  <div class="hero rounded-4 p-4 mb-4">
    <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">
      <div>
        <h2 class="mb-1">Painel da Gerência</h2>
        <div class="muted">Visão rápida: extras, folgas, atestados e tickets.</div>
      </div>
      <div class="d-flex gap-2">
        <a class="btn btn-soft" href="{{ url_for('manager.monthly_schedule') }}">Criar/editar escala mensal</a>
        <a class="btn btn-soft" href="{{ url_for('manager.tickets') }}">Ver tickets</a>
      </div>
    </div>
  </div>

  <div class="row g-3 mb-4">
    <div class="col-md-3">
      <div class="card p-3">
        <div class="muted">Extras no mês</div>
        <div class="display-6">{{ extras }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card p-3">
        <div class="muted">Folgas (abertas)</div>
        <div class="display-6">{{ folgas_abertas }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card p-3">
        <div class="muted">Atestados pendentes</div>
        <div class="display-6">{{ atestados_pendentes }}</div>
      </div>
    </div>
    <div class="col-md-3">
      <div class="card p-3">
        <div class="muted">Tickets abertos</div>
        <div class="display-6">{{ tickets_abertos }}</div>
      </div>
    </div>
  </div>

  <div class="card p-3">
    <div class="d-flex align-items-center justify-content-between">
      <h5 class="mb-0">Alertas (Folga nas próximas 24h)</h5>
      <span class="badge badge-soft">{{ alerts_due|length }}</span>
    </div>
    <div class="muted mb-2">Se tiver folga prevista, aparece aqui para não desfalcar o setor.</div>

    {% if alerts_due|length == 0 %}
      <div class="muted">Nenhum alerta no momento.</div>
    {% else %}
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>Quando</th>
              <th>Detalhes</th>
            </tr>
          </thead>
          <tbody>
          {% for a in alerts_due %}
            <tr>
              <td>{{ a.scheduled_for }}</td>
              <td><code>{{ a.payload_json }}</code></td>
            </tr>
          {% endfor %}
          </tbody>
        </table>
      </div>
    {% endif %}
  </div>
{% endblock %}
"""))

w("app/templates/manager/monthly_create.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Escala mensal" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link active" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link" href="{{ url_for('manager.tickets') }}">💬 Tickets</a>
{% endblock %}

{% block content %}
  <div class="card p-4">
    <h4 class="mb-1">Criar escala mensal</h4>
    <div class="muted mb-3">Selecione o setor e o mês. Depois você adiciona profissionais e turnos.</div>

    <form method="post" class="row g-3">
      <div class="col-md-5">
        <label class="form-label">Setor</label>
        <select class="form-select" name="sector_id" required>
          {% for s in sectors %}
            <option value="{{ s.id }}">{{ s.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">Ano</label>
        <input class="form-control" type="number" name="year" value="{{ (now() if false else '') }}" placeholder="2026" required />
      </div>
      <div class="col-md-2">
        <label class="form-label">Mês</label>
        <input class="form-control" type="number" min="1" max="12" name="month" placeholder="1" required />
      </div>
      <div class="col-12">
        <button class="btn btn-primary">Criar</button>
      </div>
    </form>
  </div>
{% endblock %}
"""))

w("app/templates/manager/monthly_edit.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Editar escala mensal" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link active" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link" href="{{ url_for('manager.tickets') }}">💬 Tickets</a>
{% endblock %}

{% block content %}
  <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
    <div>
      <h3 class="mb-0">Escala mensal — {{ sector.name }}</h3>
      <div class="muted">{{ sched.month }}/{{ sched.year }} • ID {{ sched.id }}</div>
    </div>
    <a class="btn btn-soft" href="{{ url_for('manager.monthly_schedule') }}">+ Nova escala</a>
  </div>

  <div class="row g-3">
    <div class="col-lg-4">
      <div class="card p-3">
        <h5 class="mb-2">Adicionar profissional</h5>
        <form method="post" class="d-flex gap-2">
          <select class="form-select" name="professional_id" required>
            {% for p in professionals %}
              <option value="{{ p.id }}">{{ p.category }} — {{ p.name }}</option>
            {% endfor %}
          </select>
          <button class="btn btn-primary">Adicionar</button>
        </form>
        <div class="muted mt-2" style="font-size: .9rem;">
          Após adicionar, edite o JSON de turnos por dia (ex: {"1":"D","2":"N","3":"F"}).
          Na próxima etapa, a gente troca isso por uma grade estilo Excel.
        </div>
      </div>
    </div>

    <div class="col-lg-8">
      <div class="card p-3">
        <div class="d-flex align-items-center justify-content-between">
          <h5 class="mb-0">Profissionais na escala</h5>
          <span class="badge badge-soft">{{ sched.assignments|length }}</span>
        </div>
        <div class="muted mb-2">Por enquanto, salve os turnos via JSON (rápido). Depois a gente liga a tela estilo tabela.</div>

        <form method="post" action="{{ url_for('manager.monthly_save_days', schedule_id=sched.id) }}">
          <div class="table-responsive">
            <table class="table table-sm align-middle">
              <thead>
                <tr>
                  <th>Profissional</th>
                  <th>Turnos (JSON)</th>
                </tr>
              </thead>
              <tbody>
              {% for a in sched.assignments %}
                <tr>
                  <td>{{ a.professional.category }} — {{ a.professional.name }}</td>
                  <td>
                    <textarea class="form-control" name="days_json_{{ a.id }}" rows="2">{{ a.days_json }}</textarea>
                  </td>
                </tr>
              {% endfor %}
              </tbody>
            </table>
          </div>
          <button class="btn btn-primary">Salvar turnos</button>
        </form>
      </div>
    </div>
  </div>
{% endblock %}
"""))

w("app/templates/manager/folgas.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Folgas" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link active" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link" href="{{ url_for('manager.tickets') }}">💬 Tickets</a>
{% endblock %}

{% block content %}
  <h3 class="mb-1">Folgas</h3>
  <div class="muted mb-3">A gerência pode ajustar a data (por erro ou necessidade operacional).</div>

  <div class="card p-3">
    <div class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>ID</th>
            <th>Posição</th>
            <th>Tipo</th>
            <th>Data folga</th>
            <th>Status</th>
            <th>Ajustar</th>
          </tr>
        </thead>
        <tbody>
        {% for f in folgas %}
          <tr>
            <td>#{{ f.id }}</td>
            <td>{{ f.position.position_key }}</td>
            <td><span class="badge badge-soft">{{ f.coverage_type }}</span></td>
            <td>{{ f.off_date }}</td>
            <td>{{ f.status }}</td>
            <td>
              <form method="post" class="d-flex gap-2">
                <input type="hidden" name="event_id" value="{{ f.id }}" />
                <input class="form-control form-control-sm" type="date" name="off_date" value="{{ f.off_date }}" />
                <button class="btn btn-sm btn-primary">Salvar</button>
              </form>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
{% endblock %}
"""))

w("app/templates/manager/atestados.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Atestados" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link active" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link" href="{{ url_for('manager.tickets') }}">💬 Tickets</a>
{% endblock %}

{% block content %}
  <h3 class="mb-1">Atestados</h3>
  <div class="muted mb-3">Aprovação da gerência: ao aprovar, a ausência pode ser marcada como ATESTADO no dia.</div>

  <div class="card p-3">
    <div class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Profissional</th>
            <th>Início</th>
            <th>Fim</th>
            <th>Status</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
        {% for a in atestados %}
          <tr>
            <td>{{ a.professional.name }}</td>
            <td>{{ a.start_date }}</td>
            <td>{{ a.end_date }}</td>
            <td><span class="badge badge-soft">{{ a.status }}</span></td>
            <td class="d-flex gap-2">
              <form method="post">
                <input type="hidden" name="req_id" value="{{ a.id }}" />
                <button class="btn btn-sm btn-success" name="action" value="approve">Aprovar</button>
                <button class="btn btn-sm btn-danger" name="action" value="reject">Rejeitar</button>
              </form>
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
{% endblock %}
"""))

w("app/templates/manager/tickets.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Tickets" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('manager.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('manager.monthly_schedule') }}">🗓️ Escala mensal</a>
  <a class="nav-link" href="{{ url_for('manager.folgas') }}">🟣 Folgas</a>
  <a class="nav-link" href="{{ url_for('manager.atestados') }}">🧾 Atestados</a>
  <a class="nav-link active" href="{{ url_for('manager.tickets') }}">💬 Tickets</a>
{% endblock %}

{% block content %}
  <h3 class="mb-1">Solicitações / Elogios / Reclamações</h3>
  <div class="muted mb-3">Triagem da gerência. Você pode encerrar tickets após tratativa.</div>

  <div class="card p-3">
    <div class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Assunto</th>
            <th>Setor</th>
            <th>Status</th>
            <th>Data</th>
            <th>Ação</th>
          </tr>
        </thead>
        <tbody>
        {% for t in tickets %}
          <tr>
            <td><span class="badge badge-soft">{{ t.ticket_type }}</span></td>
            <td>
              <div class="fw-semibold">{{ t.subject }}</div>
              <div class="muted" style="font-size:.9rem;">{{ t.message[:140] }}{% if t.message|length > 140 %}…{% endif %}</div>
            </td>
            <td>{{ t.sector.name if t.sector else "-" }}</td>
            <td>{{ t.status }}</td>
            <td>{{ t.created_at }}</td>
            <td>
              {% if t.status == "OPEN" %}
              <form method="post">
                <input type="hidden" name="ticket_id" value="{{ t.id }}" />
                <button class="btn btn-sm btn-primary" name="action" value="close">Encerrar</button>
              </form>
              {% else %}
                <span class="muted">—</span>
              {% endif %}
            </td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
{% endblock %}
"""))

# Nurse templates
w("app/templates/nurse/dashboard.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Painel do Enfermeiro" %}
{% block sidebar %}
  <a class="nav-link active" href="{{ url_for('nurse.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('nurse.daily') }}">📋 Escala do dia</a>
  <a class="nav-link" href="{{ url_for('nurse.enviar_atestado') }}">🧾 Enviar atestado</a>
{% endblock %}

{% block content %}
  <div class="hero rounded-4 p-4 mb-4">
    <h2 class="mb-1">Escala do dia (rápida)</h2>
    <div class="muted">Selecione setor, data e turno. O sistema sugere quem está escalado no mês, e você ajusta trocas/remanejos.</div>
    <div class="mt-3">
      <a class="btn btn-primary" href="{{ url_for('nurse.daily') }}">Abrir escala do dia</a>
    </div>
  </div>

  <div class="card p-3">
    <h5 class="mb-2">Setores cadastrados</h5>
    <div class="d-flex flex-wrap gap-2">
      {% for s in sectors %}
        <span class="badge badge-soft">{{ s.name }}</span>
      {% endfor %}
    </div>
  </div>
{% endblock %}
"""))

w("app/templates/nurse/daily.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Escala do dia" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('nurse.dashboard') }}">🏠 Painel</a>
  <a class="nav-link active" href="{{ url_for('nurse.daily') }}">📋 Escala do dia</a>
  <a class="nav-link" href="{{ url_for('nurse.enviar_atestado') }}">🧾 Enviar atestado</a>
{% endblock %}

{% block content %}
  <h3 class="mb-1">Escala do dia</h3>
  <div class="muted mb-3">Ajuste trocas, faltas, remanejamentos e extras. Tudo fica registrado para a gerência.</div>

  <div class="card p-3 mb-3">
    <form method="get" class="row g-2 align-items-end">
      <div class="col-md-4">
        <label class="form-label">Setor</label>
        <select class="form-select" name="sector_id">
          {% for s in sectors %}
            <option value="{{ s.id }}" {% if s.id == sector_id %}selected{% endif %}>{{ s.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label">Data</label>
        <input class="form-control" type="date" name="shift_date" value="{{ shift_date }}" />
      </div>
      <div class="col-md-2">
        <label class="form-label">Turno</label>
        <select class="form-select" name="turn">
          <option value="D" {% if turn=="D" %}selected{% endif %}>D</option>
          <option value="N" {% if turn=="N" %}selected{% endif %}>N</option>
        </select>
      </div>
      <div class="col-md-3">
        <button class="btn btn-soft w-100" type="submit">Carregar</button>
      </div>
    </form>
  </div>

  <div class="card p-3">
    <form method="post">
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead>
            <tr>
              <th>Posição</th>
              <th>Escalado (mensal)</th>
              <th>Presente (real)</th>
              <th>Ausência</th>
              <th>Obs</th>
              <th>Cobertura</th>
            </tr>
          </thead>
          <tbody>
            {% for pos in daily_shift.positions %}
              <tr>
                <td class="fw-semibold">{{ pos.position_key }}</td>

                <td>
                  <select class="form-select form-select-sm" name="scheduled_{{ pos.id }}">
                    <option value="">—</option>
                    {% for p in professionals %}
                      <option value="{{ p.id }}" {% if pos.scheduled_professional_id==p.id %}selected{% endif %}>{{ p.category }} — {{ p.name }}</option>
                    {% endfor %}
                  </select>
                </td>

                <td>
                  <select class="form-select form-select-sm" name="actual_{{ pos.id }}">
                    <option value="">—</option>
                    {% for p in professionals %}
                      <option value="{{ p.id }}" {% if pos.actual_professional_id==p.id %}selected{% endif %}>{{ p.category }} — {{ p.name }}</option>
                    {% endfor %}
                  </select>
                </td>

                <td style="min-width: 160px;">
                  <select class="form-select form-select-sm" name="absence_{{ pos.id }}">
                    <option value="">—</option>
                    <option value="FALTA_NJ" {% if pos.absence_type=="FALTA_NJ" %}selected{% endif %}>Falta (não just.)</option>
                    <option value="FALTA_J" {% if pos.absence_type=="FALTA_J" %}selected{% endif %}>Falta (just.)</option>
                    <option value="ATESTADO" {% if pos.absence_type=="ATESTADO" %}selected{% endif %}>Atestado</option>
                  </select>
                </td>

                <td>
                  <input class="form-control form-control-sm" name="absence_note_{{ pos.id }}" value="{{ pos.absence_note or '' }}" placeholder="ex: aguardando atestado" />
                </td>

                <td style="min-width: 210px;">
                  <button class="btn btn-sm btn-soft" type="button"
                    data-bs-toggle="modal" data-bs-target="#covModal"
                    data-posid="{{ pos.id }}">
                    Registrar cobertura
                  </button>
                  <div class="muted" style="font-size:.85rem;">
                    {% if pos.coverage_events|length > 0 %}
                      {{ pos.coverage_events[-1].coverage_type }} • {{ pos.coverage_events[-1].status }}
                    {% else %}
                      —
                    {% endif %}
                  </div>
                </td>
              </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
      <button class="btn btn-primary">Salvar escala do dia</button>
    </form>
  </div>

  <!-- Cobertura Modal -->
  <div class="modal fade" id="covModal" tabindex="-1">
    <div class="modal-dialog">
      <div class="modal-content text-dark">
        <div class="modal-header">
          <h5 class="modal-title">Registrar cobertura</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <form method="post" action="{{ url_for('nurse.add_coverage') }}">
          <div class="modal-body">
            <input type="hidden" name="pos_id" id="cov_pos_id" />

            <label class="form-label">Tipo</label>
            <select class="form-select" name="coverage_type" id="cov_type">
              <option value="REMANEJO">Remanejo</option>
              <option value="EXTRA">Extra</option>
              <option value="FOLGA">Folga (compensação)</option>
            </select>

            <div class="mt-3" id="cov_origin_wrap">
              <label class="form-label">Origem (setor)</label>
              <select class="form-select" name="origin_sector_id">
                <option value="">—</option>
                {% for s in sectors %}
                  <option value="{{ s.id }}">{{ s.name }}</option>
                {% endfor %}
              </select>
              <div class="form-text">Use para remanejamento.</div>
            </div>

            <div class="mt-3 d-none" id="cov_offdate_wrap">
              <label class="form-label">Data prevista da folga (obrigatória)</label>
              <input class="form-control" type="date" name="off_date" />
              <div class="form-text">A gerência pode ajustar depois. Sistema avisa 24h antes.</div>
            </div>

            <div class="mt-3 muted" style="font-size:.9rem;">
              Regra: se o profissional não estava escalado, registre como EXTRA ou FOLGA para governança.
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" type="button" data-bs-dismiss="modal">Cancelar</button>
            <button class="btn btn-primary">Salvar</button>
          </div>
        </form>
      </div>
    </div>
  </div>
{% endblock %}

{% block scripts %}
<script>
  const modal = document.getElementById('covModal');
  modal.addEventListener('show.bs.modal', (event) => {
    const btn = event.relatedTarget;
    document.getElementById('cov_pos_id').value = btn.getAttribute('data-posid');
  });

  const typeSel = document.getElementById('cov_type');
  const offWrap = document.getElementById('cov_offdate_wrap');
  const originWrap = document.getElementById('cov_origin_wrap');

  function refresh() {
    const v = typeSel.value;
    offWrap.classList.toggle('d-none', v !== 'FOLGA');
    originWrap.classList.toggle('d-none', v === 'FOLGA');
  }
  typeSel.addEventListener('change', refresh);
  refresh();
</script>
{% endblock %}
"""))

w("app/templates/nurse/enviar_atestado.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Enviar atestado" %}
{% block sidebar %}
  <a class="nav-link" href="{{ url_for('nurse.dashboard') }}">🏠 Painel</a>
  <a class="nav-link" href="{{ url_for('nurse.daily') }}">📋 Escala do dia</a>
  <a class="nav-link active" href="{{ url_for('nurse.enviar_atestado') }}">🧾 Enviar atestado</a>
{% endblock %}

{% block content %}
  <div class="card p-4" style="max-width: 720px;">
    <h4 class="mb-1">Enviar atestado</h4>
    <div class="muted mb-3">Vai para aprovação da gerência. Depois você marca o dia como ATESTADO na escala diária.</div>

    <form method="post" class="row g-3">
      <div class="col-md-12">
        <label class="form-label">Profissional</label>
        <select class="form-select" name="professional_id" required>
          {% for p in professionals %}
            <option value="{{ p.id }}">{{ p.category }} — {{ p.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-6">
        <label class="form-label">Início</label>
        <input class="form-control" type="date" name="start_date" required />
      </div>
      <div class="col-md-6">
        <label class="form-label">Fim</label>
        <input class="form-control" type="date" name="end_date" required />
      </div>
      <div class="col-12">
        <button class="btn btn-primary">Enviar</button>
      </div>
    </form>
  </div>
{% endblock %}
"""))

# Feedback template
w("app/templates/feedback/novo.html", textwrap.dedent("""\
{% extends "layout.html" %}
{% set title = "Contato com a Gerência" %}
{% block sidebar %}
  <a class="nav-link active" href="{{ url_for('feedback.novo') }}">📨 Enviar contato</a>
  <a class="nav-link" href="{{ url_for('auth.login') }}">🔐 Login</a>
{% endblock %}

{% block content %}
  <div class="card p-4" style="max-width: 780px;">
    <h3 class="mb-1">Fale com a Gerência</h3>
    <div class="muted mb-3">Envie solicitação, elogio ou reclamação. Você pode se identificar ou enviar anônimo.</div>

    <form method="post" class="row g-3">
      <div class="col-md-4">
        <label class="form-label">Tipo</label>
        <select class="form-select" name="ticket_type">
          <option value="SOLICITACAO">Solicitação</option>
          <option value="ELOGIO">Elogio</option>
          <option value="RECLAMACAO">Reclamação</option>
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label">Setor (opcional)</label>
        <select class="form-select" name="sector_id">
          <option value="">—</option>
          {% for s in sectors %}
            <option value="{{ s.id }}">{{ s.name }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label">Seu nome (opcional)</label>
        <input class="form-control" name="name" />
      </div>

      <div class="col-md-6">
        <label class="form-label">Email (opcional)</label>
        <input class="form-control" name="email" type="email" />
      </div>
      <div class="col-md-6">
        <label class="form-label">Assunto</label>
        <input class="form-control" name="subject" required />
      </div>

      <div class="col-12">
        <label class="form-label">Mensagem</label>
        <textarea class="form-control" name="message" rows="5" required></textarea>
      </div>

      <div class="col-12 d-flex gap-2">
        <button class="btn btn-primary">Enviar</button>
        <a class="btn btn-soft" href="{{ url_for('auth.login') }}">Acessar sistema</a>
      </div>
    </form>
  </div>
{% endblock %}
"""))

# Optional React component (placeholders)
w("frontend/src/pages/Scales.tsx", open("/mnt/data/Scales.tsx","r",encoding="utf-8").read() if os.path.exists("/mnt/data/Scales.tsx") else "// (arquivo não fornecido)\n")

w("frontend/README_frontend.md", textwrap.dedent("""\
    # Frontend (opcional)
    Este patch inclui um exemplo de página React: `frontend/src/pages/Scales.tsx`.
    Se seu projeto ainda não tem frontend React, ignore esta pasta por enquanto.
"""))

# Create zip
zip_path = "/mnt/data/nurse_manager_portal_update.zip"
if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(base):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, base)
            z.write(full, rel)

zip_path

