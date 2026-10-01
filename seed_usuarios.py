"""
seed_usuarios.py
─────────────────────────────────────────────────────────────────────
Cadastra usuários iniciais direto no banco (uso único, via conexão
temporária com o Postgres de produção). Depois disso, usuários novos
devem ser cadastrados pela própria tela /usuarios do sistema.

Uso:
    DATABASE_URL=postgresql://... python3 seed_usuarios.py
─────────────────────────────────────────────────────────────────────
"""

from app.db import Base, SessionLocal, engine
from app.models import Usuario

Base.metadata.create_all(bind=engine)

NOVOS = [
    ("adm@altamidia.com", "admin"),
    ("financeiro@altamidia.com", "admin"),
]

db = SessionLocal()
try:
    for email, papel in NOVOS:
        existente = db.query(Usuario).filter(Usuario.email == email).first()
        if existente:
            print(f"- {email} já existe (papel={existente.papel}), pulando.")
            continue
        db.add(Usuario(email=email, papel=papel, ativo=True))
        print(f"+ {email} criado como {papel}.")
    db.commit()

    print("\nUsuários atuais:")
    for u in db.query(Usuario).order_by(Usuario.papel, Usuario.email).all():
        print(f"  {u.email:30s} papel={u.papel:8s} ativo={u.ativo}")
finally:
    db.close()
