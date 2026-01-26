import pandas as pd
import unidecode
import os
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
from sqlalchemy import text, inspect

app = create_app()

def reconstruir_sistema():
    with app.app_context():
        print("--- INICIANDO REESTRUTURACAO COMPLETA ---")
        
        # 1. Garante que as tabelas existam
        db.create_all()
        
        # 2. Limpeza segura (Ignora se a tabela nao existe)
        print("🧹 Limpando dados antigos com seguranca...")
        tabelas = ["nursing_monthly_cells", "nursing_monthly_members", "nursing_monthly_schedules", "users", "sectors"]
        for tabela in tabelas:
            try:
                db.session.execute(text(f"DELETE FROM {tabela}"))
            except:
                pass
        db.session.commit()

        # 3. Criar Setores
        setores = {}
        nomes_setores = ["INTERNACAO 1° ANDAR", "INTERNACAO 2° ANDAR", "CME", "CENTRO CIRURGICO"]
        for nome in nomes_setores:
            s = Sector(name=nome, active=True)
            db.session.add(s)
            db.session.commit()
            setores[nome] = s
            # Criar escala de Janeiro
            esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
            db.session.add(esc)
            db.session.commit()
            print(f"Setor e Escala criados: {nome}")

        # 4. Criar Gerente Geral (9001)
        gerente = User(
            nome='Gerente Geral', 
            matricula='9001', 
            role='admin', 
            status='active', 
            sector_id=setores["INTERNACAO 1° ANDAR"].id,
            nascimento=date(1980,1,1)
        )
        gerente.set_password('admin')
        db.session.add(gerente)

        # 5. Importar do CSV
        try:
            df = pd.read_csv('1.csv', skiprows=1, encoding='latin1')
            print("👥 Distribuindo colaboradores entre 1° e 2° andar...")
            
            for i, row in df.iterrows():
                nome = str(row.iloc[0]).strip()
                if not nome or 'nan' in nome.lower() or 'PLANT' in nome.upper(): continue
                
                # Se i for par vai pro 1º, se for impar vai pro 2º
                setor_alvo = "INTERNACAO 1° ANDAR" if i % 2 == 0 else "INTERNACAO 2° ANDAR"
                s_id = setores[setor_alvo].id
                escala_ref = NursingMonthlySchedule.query.filter_by(sector_id=s_id).first()

                login = unidecode.unidecode(nome.split()[0].lower()) + str(i)
                user = User(
                    nome=nome, matricula=login, 
                    role='nurse' if 'Enf' in str(row.iloc[1]) else 'technician', 
                    status='active', sector_id=s_id, nascimento=date(1990,1,1)
                )
                user.set_password('123')
                db.session.add(user)
                db.session.commit()

                db.session.add(NursingMonthlyMember(schedule_id=escala_ref.id, user_id=user.id))
                
                # Turnos
                for dia in range(1, 32):
                    try:
                        val = str(row.iloc[dia + 2]).strip().upper()
                        shift = 'D' if val == 'SD' else 'N' if val == 'SN' else None
                        if shift:
                            db.session.add(NursingMonthlyCell(schedule_id=escala_ref.id, planned_user_id=user.id, day=dia, shift=shift))
                    except: continue
            
            db.session.commit()
            print("--- ✅ SUCESSO: TUDO RECONFIGURADO! ---")
            print("Acesse com 9001 / admin")
        except Exception as e:
            print(f"❌ Erro na importacao: {e}")

if __name__ == '__main__':
    reconstruir_sistema()
