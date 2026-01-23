import pandas as pd
import unidecode
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
from sqlalchemy import text

app = create_app()

def limpar_e_popular():
    with app.app_context():
        print("🧹 Limpando banco de dados...")
        # Deletar dados na ordem correta devido às chaves estrangeiras
        db.session.execute(text("DELETE FROM nursing_monthly_cells"))
        db.session.execute(text("DELETE FROM nursing_monthly_members"))
        db.session.execute(text("DELETE FROM nursing_monthly_schedules"))
        db.session.execute(text("DELETE FROM users"))
        db.session.execute(text("DELETE FROM sectors"))
        db.session.commit()

        print("📖 Lendo arquivo 1.csv...")
        # 1. Identificar Setor pelo cabeçalho do CSV
        with open('1.csv', 'r', encoding='utf-8') as f:
            first_line = f.readline()
        
        try:
            # Extrai "INTERNAÇÃO 1° ANDAR" da linha 1
            sector_name = first_line.split('DEPARTAMENTO:')[1].split('MÊS:')[0].strip()
        except:
            sector_name = "INTERNAÇÃO 1º ANDAR"

        # 2. Criar Setor
        setor = Sector(name=sector_name, active=True)
        db.session.add(setor)
        db.session.commit()
        print(f"🏢 Setor criado: {sector_name}")

        # 3. Criar Gerente (9001)
        gerente = User(
            matricula='9001',
            nome='Gerente Care',
            role='admin',
            status='active',
            sector_id=setor.id,
            first_login=False
        )
        gerente.set_password('admin')
        db.session.add(gerente)

        # 4. Criar Escala de Janeiro/2026
        escala = NursingMonthlySchedule(
            year=2026, month=1, 
            sector_id=setor.id, 
            status='published'
        )
        db.session.add(escala)
        db.session.commit()

        # 5. Processar Funcionários
        df = pd.read_csv('1.csv', skiprows=1)
        
        for _, row in df.iterrows():
            nome_completo = str(row['FUNCIONÁRIOS']).strip()
            cargo = str(row['CARGO']).strip()
            
            # Pula linhas de separação (ex: "PLANTÃO DIURNO")
            if not nome_completo or nome_completo == 'nan' or 'PLANTÃO' in nome_completo.upper():
                continue
            
            # Gerar Login (Primeiro nome sem acento)
            login = unidecode.unidecode(nome_completo.split()[0].lower())
            
            # Criar Usuário
            user = User(
                nome=nome_completo,
                matricula=login,
                role='nurse' if 'Enfermeir' in cargo else 'technician',
                status='active',
                sector_id=setor.id,
                first_login=True # Vai pedir para trocar senha no 1º acesso
            )
            user.set_password('123') # Senha padrão
            db.session.add(user)
            db.session.commit()

            # Adicionar na escala
            db.session.add(NursingMonthlyMember(schedule_id=escala.id, user_id=user.id))

            # Preencher plantões (Dias 1 a 31)
            for dia in range(1, 32):
                if str(dia) in df.columns:
                    plantao = str(row[str(dia)]).strip().upper()
                    if plantao in ['SD', 'SN']:
                        turno = 'D' if plantao == 'SD' else 'N'
                        db.session.add(NursingMonthlyCell(
                            schedule_id=escala.id,
                            planned_user_id=user.id,
                            day=dia,
                            shift=turno
                        ))
        
        db.session.commit()
        print(f"✅ Sucesso! Gerente 9001 criado e escala de Janeiro populada.")

if __name__ == "__main__":
    limpar_e_popular()