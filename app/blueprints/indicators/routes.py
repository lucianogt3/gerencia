<<<<<<< HEAD
from __future__ import annotations
=======
﻿from __future__ import annotations
>>>>>>> 0dfc06d (Atualizações no projeto)

from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models.indicator_daily import IndicatorDaily
from .forms import IndicatorForm

bp = Blueprint("indicators", __name__, url_prefix="/indicators")


def _user_unit() -> str:
    return (getattr(current_user, "setor", None)
            or getattr(current_user, "unidade", None)
            or "Unidade").strip()


def _normalize_shift(s: str | None) -> str:
    s = (s or "").strip().upper()
    if s in ("D", "DIURNO", "DAY"):
        return "D"
    if s in ("N", "NOTURNO", "NIGHT"):
        return "N"
    return "D"


def _parse_ref_date(arg: str | None) -> date:
    if not arg:
        return date.today()
    try:
        return datetime.strptime(arg, "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _day_status(ref: date, unit: str) -> tuple[str, set[str]]:
    recs = IndicatorDaily.query.filter_by(ref_date=ref, unit=unit).all()
    shifts = {_normalize_shift(r.shift) for r in recs}
    if shifts == {"D", "N"}:
        return "COMPLETO", shifts
    if len(shifts) == 1:
        return "PARCIAL", shifts
    return "PENDENTE", shifts


@bp.route("/", methods=["GET", "POST"])
@login_required
def indicators_home():
    unit = _user_unit()
    ref = _parse_ref_date(request.args.get("date"))

    # turno pelo querystring ou pelo usuário, mas sempre normaliza
    shift = _normalize_shift(request.args.get("shift") or getattr(current_user, "turno", None))

    form = IndicatorForm()

    # GET: define turno inicial
    if request.method == "GET":
        form.shift.data = shift

    # POST: turno vem do formulário
    if request.method == "POST":
        shift = _normalize_shift(form.shift.data)

    # busca registro do turno do dia
    existing = IndicatorDaily.query.filter_by(ref_date=ref, unit=unit, shift=shift).first()

    # Preenche formulário com dados existentes no GET
    if existing and request.method == "GET":
        for attr in [
            "lpp_total","lpp_admitidos","lpp_novos",
            "svd_total","sne_gtt_total","perda_sne_gtt",
            "cvc_cdl_total","perda_cvc_cdl",
            "avp_total",
            "flebite_infeccao_cvc_cdl",
            "quedas","erros_med","faltou_kit_medicacao",
            "pulseira_ok","identificacao_incorreta",
            "encaminhado_uti","paradas","obitos",
        ]:
            getattr(form, attr).data = getattr(existing, attr) or 0
        form.observacoes.data = existing.observacoes or ""
<<<<<<< HEAD
=======
        
>>>>>>> 0dfc06d (Atualizações no projeto)

    if form.validate_on_submit():
        try:
            rec = existing or IndicatorDaily(ref_date=ref, unit=unit, shift=shift)
            rec.created_by = getattr(current_user, "id", None)
            rec.shift = shift  # garante D/N

            rec.from_form(form)

            db.session.add(rec)
            db.session.commit()

            status, shifts_present = _day_status(ref, unit)
            if status == "COMPLETO":
                flash(f"✅ Dia fechado ({ref.strftime('%d/%m/%Y')}): Diurno + Noturno lançados.", "success")
            else:
                falta = "Noturno (N)" if shifts_present == {"D"} else "Diurno (D)"
                flash(f"⚠️ Turno {shift} salvo. Falta {falta} para fechar o dia.", "warning")

            return redirect(url_for("indicators.indicators_home", date=ref.strftime("%Y-%m-%d"), shift=shift))

        except Exception as e:
            db.session.rollback()
            flash(f"Erro ao salvar: {str(e)}", "danger")

    day_status, shifts_present = _day_status(ref, unit)

    return render_template(
        "indicators/index.html",
        form=form,
        ref=ref,
        unit=unit,
        shift=shift,
        day_status=day_status,
        shifts_present=shifts_present,
    )


@bp.route("/dashboard")
@login_required
def indicators_dashboard():
    unit = _user_unit()
    today = date.today()
    days = request.args.get("days", 30, type=int)
    start = today - timedelta(days=days)

    data = (IndicatorDaily.query
            .filter(IndicatorDaily.unit == unit,
                    IndicatorDaily.ref_date >= start,
                    IndicatorDaily.ref_date <= today)
            .order_by(IndicatorDaily.ref_date.desc(), IndicatorDaily.shift.asc())
            .all())

    # status por dia
    status_map: dict[date, str] = {}
    shifts_map: dict[date, list[str]] = {}
    for r in data:
        if r.ref_date not in status_map:
            st, sh = _day_status(r.ref_date, unit)
            status_map[r.ref_date] = st
            shifts_map[r.ref_date] = sorted(list(sh))

    # totais no período (somando os turnos)
    total_quedas = sum((i.quedas or 0) for i in data)
    total_erros = sum((i.erros_med or 0) for i in data)
    total_lpp_novos = sum((i.lpp_novos or 0) for i in data)
    total_paradas = sum((i.paradas or 0) for i in data)
    total_obitos = sum((i.obitos or 0) for i in data)

    # série por dia (D+N somados)
    by_date: dict[date, dict[str, int]] = {}
    for r in data:
        by_date.setdefault(r.ref_date, {"lpp_novos": 0, "quedas": 0, "erros_med": 0})
        by_date[r.ref_date]["lpp_novos"] += (r.lpp_novos or 0)
        by_date[r.ref_date]["quedas"] += (r.quedas or 0)
        by_date[r.ref_date]["erros_med"] += (r.erros_med or 0)

    last_dates = sorted(by_date.keys())[-15:]
    labels = [d.strftime("%d/%m") for d in last_dates]
    lpp_series = [by_date[d]["lpp_novos"] for d in last_dates]
    quedas_series = [by_date[d]["quedas"] for d in last_dates]
    erros_series = [by_date[d]["erros_med"] for d in last_dates]

    return render_template(
        "indicators/dashboard.html",
        unit=unit,
        today=today.strftime("%d/%m/%Y"),
        indicators=data[:60],
        status_map=status_map,
        shifts_map=shifts_map,
        total_quedas=total_quedas,
        total_erros=total_erros,
        total_lpp_novos=total_lpp_novos,
        total_paradas=total_paradas,
        total_obitos=total_obitos,
        dates=labels,
        lpp_novos_data=lpp_series,
        quedas_data=quedas_series,
        erros_data=erros_series,
    )


@bp.route("/api/dashboard-data")
@login_required
def dashboard_data():
    try:
        unit = _user_unit()
        today = date.today()
        days = request.args.get("days", 15, type=int)
        start = today - timedelta(days=days)

        data = (IndicatorDaily.query
                .filter(IndicatorDaily.unit == unit,
                        IndicatorDaily.ref_date >= start)
                .order_by(IndicatorDaily.ref_date.asc())
                .all())

        by_date: dict[date, dict[str, int]] = {}
        for r in data:
            by_date.setdefault(r.ref_date, {"lpp_novos": 0, "quedas": 0, "erros_med": 0})
            by_date[r.ref_date]["lpp_novos"] += (r.lpp_novos or 0)
            by_date[r.ref_date]["quedas"] += (r.quedas or 0)
            by_date[r.ref_date]["erros_med"] += (r.erros_med or 0)

        dates = sorted(by_date.keys())
        return jsonify({
            "success": True,
            "dates": [d.strftime("%d/%m") for d in dates],
            "lpp_novos": [by_date[d]["lpp_novos"] for d in dates],
            "quedas": [by_date[d]["quedas"] for d in dates],
            "erros": [by_date[d]["erros_med"] for d in dates],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
