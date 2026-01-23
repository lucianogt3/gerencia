from __future__ import annotations
import unidecode
from datetime import date
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import (
    NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
)

app = create_app()

def run_seed():
    with app.app_context():
        print("--- 🗑️  Limpando Banco e 🏗️ Criando Estrutura ---")
        db.drop_all()
        db.create_all()
        
        setores = {
            "p1": Sector(name="INTERNACAO 1° ANDAR", active=True),
            "p2": Sector(name="INTERNACAO 2° ANDAR", active=True),
            "cme": Sector(name="CME", active=True),
            "cc": Sector(name="CENTRO CIRURGICO", active=True)
        }
        db.session.add_all(setores.values())
        db.session.commit()

        admin = User(nome='Gerente Geral', matricula='9001', role='admin', status='active', nascimento=date(1980,1,1))
        admin.set_password('admin')
        admin.first_login = False
        db.session.add(admin)

        escalas = {}
        for k, s in setores.items():
            esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
            db.session.add(esc)
            db.session.commit()
            escalas[k] = esc

        equipe_p1 = [
            ("Claudia Magalhaes Mamare", "nurse", "PAR"), ("Isabella Sabrina Arantes Borges", "technician", "PAR"),
            ("Angelice da Cunha e Souza Coelho", "technician", "PAR"), ("Patricia Batista Nunes", "technician", "PAR"),
            ("Carlos Henrique Monteiro", "condutor", "PAR"), ("Ana Paula Timotio Vieira", "nurse", "IMPAR"),
            ("Fabio Ribeiro da Silva", "technician", "IMPAR"), ("Otaciana Coimbra", "technician", "IMPAR"),
            ("Eva Rosana Vieira da Silva", "technician", "IMPAR"), ("Jose Erivan Batista da Cruz", "condutor", "IMPAR"),
            ("Silvaneide De Oliveira Lopes", "nurse", "PAR_NOT"), ("Eva Barreto de Lima", "technician", "PAR_NOT"),
            ("Ana Carolina Modesto da Silva", "technician", "PAR_NOT"), ("Sirleide de Queiroz Monteiro", "technician", "PAR_NOT"),
            ("Ana Katia", "nurse", "IMPAR_NOT"), ("Marcia Batista Vieria Amancio", "technician", "IMPAR_NOT"),
            ("Gisele da Conceicao Alves", "technician", "IMPAR_NOT"), ("Edneta Alecrim", "technician", "IMPAR_NOT")
        ]
        
        equipe_p2 = [
            ("Elisvania de Araujo Silva Leles", "technician", "PAR"), ("Thamires Alves do Amaral da Silva", "technician", "PAR"),
            ("Ana Claudia de Almeida Vaz Reis", "technician", "PAR"), ("Edna de Jesus", "nurse", "IMPAR"),
            ("Edneide do Nascimento Ribeiro", "technician", "IMPAR"), ("Delma Gomes de Moraes", "technician", "IMPAR"),
            ("Gabriel Vieira da Silva Borges", "technician", "IMPAR"), ("Fernando Henrique Paiva da Silva", "nurse", "PAR_NOT"),
            ("Luana da Costa Sena", "technician", "PAR_NOT"), ("Eudes Ferreira Fideles", "technician", "PAR_NOT"),
            ("Joelma Goncalves de Brito", "technician", "PAR_NOT"), ("Gabriela Flauzina de Oliveira", "nurse", "IMPAR_NOT"),
            ("Erica Marques de Oliveira", "technician", "IMPAR_NOT"), ("Olivia Dourado dos Santos", "technician", "IMPAR_NOT"),
            ("Eliane Nunes Pereira", "technician", "IMPAR_NOT"), ("Priscilla Dayana Alves Barros", "nurse", "ADM")
        ]

        def process_list(lista, setor_key):
            for i, (nome, cargo, padrao) in enumerate(lista):
                nome_limpo = unidecode.unidecode(nome).lower()
                partes = nome_limpo.split()
                login = f"{partes[0]}.{partes[-1]}"
                u = User(nome=nome, matricula=login, email=f"{login}@hospital.com", role=cargo, 
                         status="active", sector_id=setores[setor_key].id, nascimento=date(1990,1,1))
                u.set_password("123456")
                u.first_login = True
                db.session.add(u)
                db.session.commit()
                db.session.add(NursingMonthlyMember(schedule_id=escalas[setor_key].id, user_id=u.id))
                for dia in range(1, 32):
                    shift = None
                    if padrao == "PAR" and dia % 2 == 0: shift = "D"
                    elif padrao == "IMPAR" and dia % 2 != 0: shift = "D"
                    elif padrao == "PAR_NOT" and dia % 2 == 0: shift = "N"
                    elif padrao == "IMPAR_NOT" and dia % 2 != 0: shift = "N"
                    elif padrao == "ADM": shift = "D"
                    if shift:
                        db.session.add(NursingMonthlyCell(schedule_id=escalas[setor_key].id, planned_user_id=u.id, day=dia, shift=shift))
        
        process_list(equipe_p1, "p1")
        process_list(equipe_p2, "p2")
        db.session.commit()
        print("--- ✅ SUCESSO TOTAL ---")

if __name__ == '__main__':
    run_seed()
