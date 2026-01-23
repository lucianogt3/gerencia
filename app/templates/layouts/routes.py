from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import date
from app.models import Sector

bp = Blueprint("nursing", __name__, url_prefix="/nursing")

from datetime import date # Certifique-se de que este import está no topo do arquivo



usuários
@login_required
def daily():
    # 1. Define a data de hoje (ou a data que você quer exibir)
    hoje = dt_date.today()
    
    # 2. Busca os dados da escala (lógica que discutimos antes)
    # Aqui é apenas um exemplo do que você deve ter buscado no banco
    user_sector_id = getattr(current_user, "sector_id", None)
    sector_name = current_user.sector.name if current_user.sector else "Sem Setor"
    
    # Lógica para popular planned_staff...
    planned_staff = [] 

    # 3. O SEGREDO: Você PRECISA passar date=hoje aqui dentro
    return render_template(
        "nursing/daily.html", 
        date=hoje,              # <--- Isso resolve o seu erro!
        planned_staff=planned_staff,
        sector_name=sector_name
    )
    )
