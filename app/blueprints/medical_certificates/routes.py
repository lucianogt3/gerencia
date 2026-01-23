from __future__ import annotations

import os
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models.sick_note import SickNote
from app.models.user import User  # ✅ para puxar nome/setor/turno do cadastro

bp = Blueprint("medical_certificates", __name__, url_prefix="/medical-certificates")

UPLOAD_FOLDER = os.path.join("app", "static", "uploads", "sick_notes")
ALLOWED_EXT = {"pdf", "png", "jpg", "jpeg"}


def _is_manager() -> bool:
    return getattr(current_user, "role", "") in ("manager", "admin")


def _save_file(file_storage):
    """Upload opcional (PDF ou imagem)."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return (None, None)

    original_name = file_storage.filename
    ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
    if ext not in ALLOWED_EXT:
        raise ValueError("Arquivo inválido. Envie PDF ou imagem (png/jpg).")

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_name = f"sick_{getattr(current_user,'id','x')}_{stamp}.{ext}"
    file_storage.save(os.path.join(UPLOAD_FOLDER, safe_name))

    return (safe_name, original_name)


@bp.route("/", methods=["GET"])
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()

    query = SickNote.query

    # colaborador vê somente os próprios
    if not _is_manager():
        query = query.filter_by(matricula=(getattr(current_user, "matricula", "") or ""))

    # filtro status
    if status in ("pending", "approved", "rejected"):
        query = query.filter(SickNote.status == status)

    # filtro busca
    if q:
        like = f"%{q}%"
        query = query.filter((SickNote.matricula.ilike(like)) | (SickNote.nome.ilike(like)))

    notes = query.order_by(SickNote.created_at.desc()).all()

    return render_template(
        "medical_certificates/index.html",
        notes=notes,
        is_manager=_is_manager(),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    """
    ✅ Colaborador: usa dados do current_user
    ✅ Gerente: digita só matrícula e sistema puxa nome/setor/turno do cadastro (User)
    """
    is_manager = _is_manager()

    if request.method == "POST":
        data_atestado = (request.form.get("data_atestado") or "").strip()
        dias = (request.form.get("dias") or "").strip()
        cid = (request.form.get("cid") or "").strip() or None

        # obrigatórios
        if not data_atestado or not dias:
            flash("Data do atestado e quantidade de dias são obrigatórios.", "error")
            return redirect(url_for("medical_certificates.new"))

        try:
            dias_int = int(dias)
            if dias_int < 1:
                raise ValueError()
        except Exception:
            flash("Quantidade de dias inválida.", "error")
            return redirect(url_for("medical_certificates.new"))

        try:
            dt = datetime.strptime(data_atestado, "%Y-%m-%d").date()
        except Exception:
            flash("Data do atestado inválida.", "error")
            return redirect(url_for("medical_certificates.new"))

        # upload opcional
        file = request.files.get("file")
        try:
            filename, original_name = _save_file(file)
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("medical_certificates.new"))

        # =========================
        # ✅ DADOS DO COLABORADOR
        # =========================
        if is_manager:
            matricula = (request.form.get("matricula") or "").strip()
            if not matricula:
                flash("Matrícula do colaborador é obrigatória.", "error")
                return redirect(url_for("medical_certificates.new"))

            # ✅ obrigatoriamente deve existir para puxar dados
            u = User.query.filter_by(matricula=matricula).first()
            if not u:
                flash("Matrícula não encontrada no sistema. Cadastre o colaborador antes de lançar o atestado.", "error")
                return redirect(url_for("medical_certificates.new"))

            nome = getattr(u, "nome", None)
            setor = getattr(u, "setor", None)
            turno = getattr(u, "turno", None)

        else:
            matricula = (getattr(current_user, "matricula", "") or "").strip()
            if not matricula:
                flash("Sua matrícula não está definida no cadastro. Solicite ao gerente.", "error")
                return redirect(url_for("medical_certificates.index"))

            nome = getattr(current_user, "nome", None)
            setor = getattr(current_user, "setor", None)
            turno = getattr(current_user, "turno", None)

        # =========================
        # ✅ SALVAR (TRAVA)
        # =========================
        note = SickNote(
            matricula=matricula,
            nome=nome,
            setor=setor,
            turno=turno,
            data_atestado=dt,
            dias=dias_int,
            filename=filename,
            original_name=original_name,
            cid=cid,  # ✅ se existir no model
            status="pending",
            created_at=datetime.utcnow(),
        )

        db.session.add(note)
        db.session.commit()

        flash("Atestado salvo e enviado para aprovação.", "success")

        # ✅ melhor retorno: lista de atestados (gerente e colaborador veem)
        return redirect(url_for("medical_certificates.index"))

    return render_template("medical_certificates/new.html", is_manager=is_manager)


@bp.route("/download/<int:note_id>", methods=["GET"])
@login_required
def download(note_id: int):
    note = SickNote.query.get_or_404(note_id)

    # colaborador só baixa o próprio; gerente baixa qualquer
    if not _is_manager():
        if note.matricula != (getattr(current_user, "matricula", "") or ""):
            abort(403)

    if not note.filename:
        abort(404)

    return send_from_directory(
        UPLOAD_FOLDER,
        note.filename,
        as_attachment=True,
        download_name=(note.original_name or note.filename),
    )


@bp.route("/review/<int:note_id>", methods=["GET", "POST"])
@login_required
def review(note_id: int):
    # só gerente
    if not _is_manager():
        abort(403)

    note = SickNote.query.get_or_404(note_id)

    if request.method == "POST":
        action = request.form.get("action")
        if action not in ("approve", "reject"):
            flash("Ação inválida.", "error")
            return redirect(url_for("medical_certificates.review", note_id=note.id))

        note.status = "approved" if action == "approve" else "rejected"
        db.session.commit()

        flash("Atestado processado com sucesso.", "success")
        return redirect(url_for("medical_certificates.index"))

    return render_template("medical_certificates/review.html", note=note)
