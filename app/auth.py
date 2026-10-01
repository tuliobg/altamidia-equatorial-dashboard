import os

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.models import Usuario

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Usado só para popular a tabela de usuários na primeira vez que o sistema
# sobe (ver seed_admin_inicial em app/main.py) — depois disso, quem gerencia
# e-mails e papéis é a página /usuarios, não mais essa variável.
ALLOWED_EMAILS = {
    e.strip().lower()
    for e in os.environ.get("ALLOWED_EMAILS", "diretoria@altamidia.com").split(",")
    if e.strip()
}

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def usuario_logado(request: Request):
    """Dados da sessão (email/nome vindos do Google) — não confundir com o
    registro de permissão na tabela `usuarios`."""
    return request.session.get("user")


def obter_usuario_db(request: Request, db: Session):
    """Retorna o registro de Usuario (com o papel/permissão) para quem está
    logado, ou None se não estiver logado ou não tiver cadastro ativo."""
    sess = usuario_logado(request)
    if not sess:
        return None
    email = (sess.get("email") or "").lower()
    if not email:
        return None
    return db.query(Usuario).filter(Usuario.email == email, Usuario.ativo == True).first()  # noqa: E712


def exigir_login(request: Request, db: Session):
    """Dependency: redireciona para login se não autenticado/autorizado."""
    sess = usuario_logado(request)
    if not sess:
        return RedirectResponse(url="/login")
    usuario = obter_usuario_db(request, db)
    if not usuario:
        return RedirectResponse(url="/sem-acesso")
    return None


def exigir_admin(request: Request, db: Session):
    """Dependency: como exigir_login, mas só deixa passar quem tem papel admin."""
    redirect = exigir_login(request, db)
    if redirect:
        return redirect
    usuario = obter_usuario_db(request, db)
    if not usuario or usuario.papel != "admin":
        return RedirectResponse(url="/sem-permissao")
    return None
