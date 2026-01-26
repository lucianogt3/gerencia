import pandas as pd
import unidecode
import os
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
from sqlalchemy import text

app = create_app()

def limpar_e_popular():
    with app.app_context():
        print("--- INICIANDO POPULACAO DO SISTEMA ---")
        
        # 1. Cria as tabelas se elas nao existirem
        print("🛠️ Criando/Verificando tabelas...")
        db.create_all()

        # 2. Limpeza total (com try/except para nao travar se a tabela estiver vazia)
        print("🧹 Limpando dados antigos...")
        tabelas = ["nursing_monthly_cells", "nursing_monthly_members", "nursing_monthly_schedules", "users", "sectors"]
        for tabela in tabelas:
            try:
                db.session.execute(text(f"DELETE FROM {tabela}"))
            except Exception:
                pass
        db.session.commit()

        # 3. Leitura do CSV com tratamento de erro de acentos (latin1)
        csv_path = '1.csv'
        if not os.path.exists(csv_path):
            print(f"❌ ERRO: Arquivo {csv_path} nao encontrado na raiz!")
            return

        print("📖 Lendo 1.csv...")
        try:
            df = pd.read_csv(csv_path, skiprows=1, encoding='latin1', sep=',')
            if len(df.columns) < 2:
                df = pd.read_csv(csv_path, skiprows=1, encoding='latin1', sep=';')
        except:
            df = pd.read_csv(csv_path, skiprows=1, encoding='utf-8')

        # 4. Criar setor
        setor = Sector(name="INTERNACAO 1° ANDAR", active=True)
        db.session.add(setor)
        db.session.commit()

        # 5. Criar Gerente (9001 / admin)
        data_padrao = date(1900, 1, 1)
        gerente = User(
            nome='Gerente Care',
            matricula='9001',
            role='admin',
            status='active',
            sector_id=setor.id,
            nascimento=data_padrao,
            setor=setor.name
        )
        if hasattr(gerente, 'first_login'):
            gerente.first_login = False
        gerente.set_password('admin')
        db.session.add(gerente)

        # 6. Criar Escala Jan/2026
        escala = NursingMonthlySchedule(year=2026, month=1, sector_id=setor.id, status='published')
        db.session.add(escala)
        db.session.commit()

        print("👥 Importando equipe e escala de Janeiro...")
        matriculas_usadas = []

        for _, row in df.iterrows():
            nome_raw = row.iloc[0]
            nome = str(nome_raw).strip()
            cargo = str(row.iloc[1]).strip()
            
            if not nome or 'nan' in nome.lower() or 'PLANTÃO' in nome.upper() or 'DIURNO' in nome.upper():
                continue
            
            # Gerar Login: primeiro nome sem acento
            login_base = unidecode.unidecode(nome.split()[0].lower())
            login = login_base
            
            # Evita erro de duplicidade (ex: duas Evas)
            contador = 1
            while login in matriculas_usadas:
                login = f"{login_base}{contador}"
                contador += 1
            matriculas_usadas.append(login)
            
            user = User(
                nome=nome,
                matricula=login,
                role='nurse' if 'Enf' in cargo else 'technician',
                status='active',
                sector_id=setor.id,
                nascimento=data_padrao,
                setor=setor.name
            )
            if hasattr(user, 'first_login'):
                user.first_login = True
            
            user.set_password('123')
            db.session.add(user)
            db.session.commit()
            
            db.session.add(NursingMonthlyMember(schedule_id=escala.id, user_id=user.id))

            # Preencher dias 1 a 31
            for dia in range(1, 32):
                try:
                    p = str(row.iloc[dia + 2]).strip().upper()
                    if p in ['SD', 'SN']:
                        db.session.add(NursingMonthlyCell(
                            schedule_id=escala.id,
                            planned_user_id=user.id,
                            day=dia,
                            shift='D' if p == 'SD' else 'N'
                        ))
                except:
                    continue
        
        db.session.commit()
        print(f"✅ SUCESSO! {len(matriculas_usadas)} funcionarios importados.")
        print("Acesso Gerente: 9001 / admin")

if __name__ == "__main__":
    limpar_e_popular()
