from __future__ import annotations
import click
from datetime import date
import unidecode
from app.extensions import db
from app.models.user import User
from app.models.sector import Sector
from app.models.nursing_schedule import (
    NursingMonthlySchedule, NursingMonthlyMember, NursingMonthlyCell
)

@click.command("seed")
def seed_command():
    print("--- 🗑️  Limpando Banco e 🏗️ Criando Estrutura... ---")
    db.drop_all()
    db.create_all()
    
    # 1. CRIAR SETORES
    setores = {
        "p1": Sector(name="INTERNACAO 1° ANDAR", active=True),
        "p2": Sector(name="INTERNACAO 2° ANDAR", active=True),
        "cme": Sector(name="CME", active=True),
        "cc": Sector(name="CENTRO CIRURGICO", active=True)
    }
    db.session.add_all(setores.values())
    db.session.commit()

    # 2. GERENTE GERAL
    admin = User(nome='Gerente Geral', matricula='9001', role='admin', status='active', nascimento=date(1980,1,1))
    admin.set_password('admin')
    db.session.add(admin)

    # 3. ESCALAS DE JANEIRO 2026
    escalas = {}
    for k, s in setores.items():
        esc = NursingMonthlySchedule(year=2026, month=1, sector_id=s.id, status='published')
        db.session.add(esc)
        db.session.commit()
        escalas[k] = esc

    # --- LISTAS DE COLABORADORES POR SETOR ---

    # 🏥 INTERNAÇÃO 1° ANDAR
    equipe_p1 = [
        ("Claudia Magalhaes Mamare", "nurse", "PAR"),
        ("Isabella Sabrina Arantes Borges", "technician", "PAR"),
        ("Angelice da Cunha e Souza Coelho", "technician", "PAR"),
        ("Patricia Batista Nunes", "technician", "PAR"),
        ("Carlos Henrique Monteiro", "condutor", "PAR"),
        ("Ana Paula Timotio Vieira", "nurse", "IMPAR"),
        ("Fabio Ribeiro da Silva", "technician", "IMPAR"),
        ("Otaciana Coimbra", "technician", "IMPAR"),
        ("Eva Rosana Vieira da Silva", "technician", "IMPAR"),
        ("Jose Erivan Batista da Cruz", "condutor", "IMPAR"),
        ("Silvaneide De Oliveira Lopes", "nurse", "PAR_NOT"),
        ("Eva Barreto de Lima", "technician", "PAR_NOT"),
        ("Ana Carolina Modesto da Silva", "technician", "PAR_NOT"),
        ("Sirleide de Queiroz Monteiro", "technician", "PAR_NOT"),
        ("Ana Katia", "nurse", "IMPAR_NOT"),
        ("Marcia Batista Vieria Amancio", "technician", "IMPAR_NOT"),
        ("Gisele da Conceicao Alves", "technician", "IMPAR_NOT"),
        ("Edneta Alecrim", "technician", "IMPAR_NOT")
    ]

    # 🏥 INTERNAÇÃO 2° ANDAR
    equipe_p2 = [
        ("Elisvania de Araujo Silva Leles", "technician", "PAR"),
        ("Thamires Alves do Amaral da Silva", "technician", "PAR"),
        ("Ana Claudia de Almeida Vaz Reis", "technician", "PAR"),
        ("Edna de Jesus", "nurse", "IMPAR"),
        ("Edneide do Nascimento Ribeiro", "technician", "IMPAR"),
        ("Delma Gomes de Moraes", "technician", "IMPAR"),
        ("Gabriel Vieira da Silva Borges", "technician", "IMPAR"),
        ("Fernando Henrique Paiva da Silva", "nurse", "PAR_NOT"),
        ("Luana da Costa Sena", "technician", "PAR_NOT"),
        ("Eudes Ferreira Fideles", "technician", "PAR_NOT"),
        ("Joelma Goncalves de Brito", "technician", "PAR_NOT"),
        ("Gabriela Flauzina de Oliveira", "nurse", "IMPAR_NOT"),
        ("Erica Marques de Oliveira", "technician", "IMPAR_NOT"),
        ("Olivia Dourado dos Santos", "technician", "IMPAR_NOT"),
        ("Eliane Nunes Pereira", "technician", "IMPAR_NOT"),
        ("Priscilla Dayana Alves Barros", "nurse", "ADM")
    ]

    # 🏥 CME / CC
    equipe_cme_cc = [
        ("Maria Helena da Silva", "nurse", "ADM", "cme"),
        ("Daniela do Santos Cota", "technician", "PAR", "cme"),
        ("Neudaires Araujo de Moura", "technician", "PAR", "cme"),
        ("Daiana Ferreira", "nurse", "ADM", "cc"),
        ("Anatalia Maria S. dos Santos", "technician", "ADM", "cc"),
        ("Isabel Cristina Satana da Silva", "technician", "PAR", "cc")
    ]

    def process_list(lista, setor_key, default_setor=None):
        for i, data in enumerate(lista):
            nome, cargo, padrao = data[0], data[1], data[2]
            s_key = data[3] if len(data) > 3 else setor_key
            
            login = unidecode.unidecode(nome.split()[0].lower()) + str(i + 100)
            u = User(nome=nome, matricula=login, role=cargo, status="active", 
                     sector_id=setores[s_key].id, nascimento=date(1990,1,1))
            u.set_password("123")
            db.session.add(u)
            db.session.commit()

            db.session.add(NursingMonthlyMember(schedule_id=escalas[s_key].id, user_id=u.id))
            
            for dia in range(1, 32):
                shift = None
                if padrao == "PAR" and dia % 2 == 0: shift = "D"
                elif padrao == "IMPAR" and dia % 2 != 0: shift = "D"
                elif padrao == "PAR_NOT" and dia % 2 == 0: shift = "N"
                elif padrao == "IMPAR_NOT" and dia % 2 != 0: shift = "N"
                elif padrao == "ADM": shift = "D" # Administrativo
                
                if shift:
                    db.session.add(NursingMonthlyCell(schedule_id=escalas[s_key].id, 
                                   planned_user_id=u.id, day=dia, shift=shift))

    print("🚀 Populando 1° Andar...")
    process_list(equipe_p1, "p1")
    print("🚀 Populando 2° Andar...")
    process_list(equipe_p2, "p2")
    print("🚀 Populando CME e CC...")
    process_list(equipe_cme_cc, "cme")
    
    db.session.commit()
    print("--- ✅ SISTEMA RESTAURADO COM TODOS OS SETORES! ---")

if __name__ == '__main__':
    seed_command()