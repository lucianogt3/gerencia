import pandas as pd
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyCell
from sqlalchemy import text

app = create_app()

def corrigir_turnos():
    with app.app_context():
        print("--- INICIANDO CORREÇÃO DE TURNOS ---")
        
        # 1. Localiza a escala de Janeiro
        escala = NursingMonthlySchedule.query.filter_by(year=2026, month=1).first()
        if not escala:
            print("❌ Escala de Janeiro não encontrada!")
            return

        # Limpa células antigas para não duplicar
        db.session.execute(text(f"DELETE FROM nursing_monthly_cells WHERE schedule_id={escala.id}"))
        db.session.commit()

        # 2. Lê o CSV
        df = pd.read_csv('1.csv', skiprows=1, encoding='latin1')
        
        contagem = 0
        for _, row in df.iterrows():
            nome = str(row.iloc[0]).strip()
            
            # Busca o usuário no banco pelo nome
            user = User.query.filter_by(nome=nome).first()
            if user:
                # Percorre as colunas do dia 1 ao 31
                # No seu CSV, o dia 1 é a 4ª coluna (índice 3)
                for dia in range(1, 32):
                    try:
                        valor = str(row.iloc[dia + 2]).strip().upper()
                        
                        shift = None
                        if valor == 'SD': shift = 'D'
                        elif valor == 'SN': shift = 'N'
                        
                        if shift:
                            cell = NursingMonthlyCell(
                                schedule_id=escala.id,
                                planned_user_id=user.id,
                                day=dia,
                                shift=shift
                            )
                            db.session.add(cell)
                            contagem += 1
                    except:
                        continue
                db.session.commit()
                print(f"✅ Turnos aplicados para: {nome}")

        print(f"--- SUCESSO: {contagem} plantões inseridos! ---")

if __name__ == '__main__':
    corrigir_turnos()
