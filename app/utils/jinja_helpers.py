# app/utils/jinja_helpers.py
def month_name(m: int) -> str:
    names = [
        "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    try:
        m = int(m)
    except Exception:
        return ""
    return names[m] if 1 <= m <= 12 else ""
