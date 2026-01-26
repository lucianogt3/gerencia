import pandas as pd
import unidecode
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
from sqlalchemy import text, inspect

app = create_app()

def popular():
    with app.app_context():
        print("--- VERIFICANDO ESTRUTURA DO BANCO ---")
        db.create_all()  # Cria as tabelas se nao existirem
        
        inspector = inspect(db.engine)
        tabelas_existentes = inspector.get_table_names()
        
        print("🧹 Limpando dados antigos...")
        tabelas_para_limpar = ["nursing_monthly_cells", "nursing_monthly_members", "nursing_monthly_schedules", "users", "sectors"]
        
        for tabela in tabelas_para_limpar:
            if tabela in tabelas_existentes:
                try:
                    db.session.execute(text(f"DELETE FROM {tabela}"))
                except Exception as e:
                    print(f"Aviso ao limpar {tabela}: {e}")
        
        db.session.commit()

        # 1. Criar Setores
        setores = {}
        for nome in ["INTERNACAO 1° ANDAR", "CME", "CENTRO CIRURGICO"]:
            s = Sector(name=nome, active=True)
            db.session.add(s)
            db.session.commit()
            setores[nome] = s
            
            # Criar escala de Janeiro
            esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
            db.session.add(esc)
            db.session.commit()
            print(f"✅ Setor e Escala: {nome}")

        # 2. Gerente Geral (9001 / admin)
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

        # 3. Importar do 1.csv
        try:
            df = pd.read_csv('1.csv', skiprows=1, encoding='latin1')
            escala_ref = NursingMonthlySchedule.query.filter_by(sector_id=setores["INTERNACAO 1° ANDAR"].id).first()
            
            print("👥 Importando colaboradores...")
            for i, row in df.iterrows():
                nome = str(row.iloc[0]).strip()
                if not nome or 'nan' in nome.lower() or 'PLANT' in nome.upper(): continue
                
                login = unidecode.unidecode(nome.split()[0].lower()) + str(i)
                user = User(
                    nome=nome, matricula=login, 
                    role='nurse' if 'Enf' in str(row.iloc[1]) else 'technician', 
                    status='active', sector_id=setores["INTERNACAO 1° ANDAR"].id, 
                    nascimento=date(1990,1,1)
                )
                user.set_password('123')
                db.session.add(user)
                db.session.commit()

                db.session.add(NursingMonthlyMember(schedule_id=escala_ref.id, user_id=user.id))
                
                for dia in range(1, 32):
                    try:
                        val = str(row.iloc[dia + 2]).strip().upper()
                        shift = 'D' if val == 'SD' else 'N' if val == 'SN' else None
                        if shift:
                            db.session.add(NursingMonthlyCell(schedule_id=escala_ref.id, planned_user_id=user.id, day=dia, shift=shift))
                    except: continue
            
            db.session.commit()
            print("--- ✅ SUCESSO TOTAL ---")
        except Exception as e:
            print(f"❌ Erro no CSV: {e}")

if __name__ == '__main__':
    popular()
