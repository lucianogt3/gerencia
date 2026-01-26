import pandas as pd
import unidecode
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
from sqlalchemy import text

app = create_app()

def reconstruir_com_2_andar():
    with app.app_context():
        print("--- LIMPANDO E REORGANIZANDO SETORES ---")
        db.create_all()
        
        # Limpa tudo para evitar duplicados
        db.session.execute(text("DELETE FROM nursing_monthly_cells"))
        db.session.execute(text("DELETE FROM nursing_monthly_members"))
        db.session.execute(text("DELETE FROM nursing_monthly_schedules"))
        db.session.execute(text("DELETE FROM users"))
        db.session.execute(text("DELETE FROM sectors"))
        db.session.commit()

        # 1. Criar TODOS os setores necessários
        nomes_setores = ["INTERNACAO 1° ANDAR", "INTERNACAO 2° ANDAR", "CME", "CENTRO CIRURGICO"]
        setores = {}
        for nome in nomes_setores:
            s = Sector(name=nome, active=True)
            db.session.add(s)
            db.session.commit()
            setores[nome] = s
            # Escala de Janeiro para cada um
            esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
            db.session.add(esc)
            db.session.commit()

        # 2. Admin
        gerente = User(nome='Gerente Geral', matricula='9001', role='admin', status='active', sector_id=setores["INTERNACAO 1° ANDAR"].id)
        gerente.set_password('admin')
        db.session.add(gerente)

        # 3. Importar do CSV
        try:
            df = pd.read_csv('1.csv', skiprows=1, encoding='latin1')
            
            for i, row in df.iterrows():
                nome = str(row.iloc[0]).strip()
                if not nome or 'nan' in nome.lower() or 'PLANT' in nome.upper(): continue
                
                # LÓGICA DE SEPARAÇÃO: 
                # Se no CSV não diz o andar, vou colocar metade em cada um para você testar, 
                # ou você pode me dizer se existe uma coluna de 'Setor' no seu Excel.
                if i % 2 == 0:
                    setor_nome = "INTERNACAO 1° ANDAR"
                else:
                    setor_nome = "INTERNACAO 2° ANDAR"
                
                target_sector = setores[setor_nome]
                escala_ref = NursingMonthlySchedule.query.filter_by(sector_id=target_sector.id).first()

                login = unidecode.unidecode(nome.split()[0].lower()) + str(i)
                user = User(
                    nome=nome, matricula=login, 
                    role='nurse' if 'Enf' in str(row.iloc[1]) else 'technician', 
                    status='active', sector_id=target_sector.id, 
                    nascimento=date(1990,1,1)
                )
                user.set_password('123')
                db.session.add(user)
                db.session.commit()

                db.session.add(NursingMonthlyMember(schedule_id=escala_ref.id, user_id=user.id))
                
                # Plantões
                for dia in range(1, 32):
                    try:
                        val = str(row.iloc[dia + 2]).strip().upper()
                        shift = 'D' if val == 'SD' else 'N' if val == 'SN' else None
                        if shift:
                            db.session.add(NursingMonthlyCell(schedule_id=escala_ref.id, planned_user_id=user.id, day=dia, shift=shift))
                    except: continue
            
            db.session.commit()
            print("---  SUCESSO: 1° E 2° ANDAR CONFIGURADOS! ---")
        except Exception as e:
            print(f" Erro: {e}")

if __name__ == '__main__':
    reconstruir_com_2_andar()
