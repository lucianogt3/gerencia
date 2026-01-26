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

def popular():
    with app.app_context():
        print("--- LIMPANDO BANCO DE DADOS ---")
        db.create_all()
        
        # Limpeza profunda das tabelas na ordem correta
        db.session.execute(text("DELETE FROM nursing_monthly_cells"))
        db.session.execute(text("DELETE FROM nursing_monthly_members"))
        db.session.execute(text("DELETE FROM nursing_monthly_schedules"))
        db.session.execute(text("DELETE FROM users"))
        db.session.execute(text("DELETE FROM sectors"))
        db.session.commit()
        print("✅ Banco limpo!")

        # 1. Criar os 3 Setores
        setores = {}
        for nome in ["INTERNACAO 1° ANDAR", "CME", "CENTRO CIRURGICO"]:
            s = Sector(name=nome, active=True)
            db.session.add(s)
            db.session.commit()
            setores[nome] = s
            
            # Criar escala de Janeiro para cada um
            esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
            db.session.add(esc)
            db.session.commit()
            print(f"Setor e Escala criados: {nome}")

        # 2. Gerente Geral (Acesso: 9001 / admin)
        gerente = User(
            nome='Gerente Geral', 
            matricula='9001', 
            role='admin', 
            status='active', 
            nascimento=date(1980,1,1),
            sector_id=setores["INTERNACAO 1° ANDAR"].id
        )
        gerente.set_password('admin')
        db.session.add(gerente)
        db.session.commit()

        # 3. Importar do 1.csv para o 1° Andar
        try:
            df = pd.read_csv('1.csv', skiprows=1, encoding='latin1')
            escala_1andar = NursingMonthlySchedule.query.filter_by(sector_id=setores["INTERNACAO 1° ANDAR"].id).first()
            
            print("👥 Importando colaboradores...")
            for i, row in df.iterrows():
                nome = str(row.iloc[0]).strip()
                if not nome or 'nan' in nome.lower() or 'PLANT' in nome.upper() or 'DIURNO' in nome.upper(): 
                    continue
                
                login = unidecode.unidecode(nome.split()[0].lower()) + str(i)
                user = User(
                    nome=nome, 
                    matricula=login, 
                    role='nurse' if 'Enf' in str(row.iloc[1]) else 'technician', 
                    status='active', 
                    sector_id=setores["INTERNACAO 1° ANDAR"].id, 
                    nascimento=date(1990,1,1)
                )
                user.set_password('123')
                db.session.add(user)
                db.session.commit()

                db.session.add(NursingMonthlyMember(schedule_id=escala_1andar.id, user_id=user.id))
                
                for dia in range(1, 32):
                    try:
                        val = str(row.iloc[dia + 2]).strip().upper()
                        shift = 'D' if val == 'SD' else 'N' if val == 'SN' else None
                        if shift:
                            db.session.add(NursingMonthlyCell(
                                schedule_id=escala_1andar.id, 
                                planned_user_id=user.id, 
                                day=dia, 
                                shift=shift
                            ))
                    except:
                        continue
            
            db.session.commit()
            print("--- ✅ SUCESSO: BANCO REFEITO COM CME E CC ---")
        except Exception as e:
            print(f"❌ Erro ao ler CSV: {e}")

if __name__ == '__main__':
    popular()
