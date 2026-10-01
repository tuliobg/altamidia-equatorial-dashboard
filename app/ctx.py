from fastapi import Request
from sqlalchemy.orm import Session

from app.auth import obter_usuario_db, usuario_logado


def ctx_base(request: Request, db: Session, active: str):
    """Contexto comum a toda página logada: dados da sessão + papel (pro menu
    saber se mostra Cadastro/Lançar Fatura/Usuários)."""
    usuario = obter_usuario_db(request, db)
    return {
        "user": usuario_logado(request),
        "papel": usuario.papel if usuario else None,
        "active": active,
    }
