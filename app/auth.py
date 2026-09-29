import os

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from starlette.responses import RedirectResponse

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# Lista de e-mails autorizados a acessar o dashboard. Editável sem tocar em
# código: variável de ambiente ALLOWED_EMAILS separada por vírgula.
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
    return request.session.get("user")


def exigir_login(request: Request):
    """Dependency do FastAPI: redireciona para login se não autenticado/autorizado."""
    user = usuario_logado(request)
    if not user:
        return RedirectResponse(url="/login")
    if user.get("email", "").lower() not in ALLOWED_EMAILS:
        return RedirectResponse(url="/sem-acesso")
    return None
