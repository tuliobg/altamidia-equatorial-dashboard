import os
from datetime import datetime

from fastapi import Depends, FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse

from app.auth import ALLOWED_EMAILS, exigir_login, oauth, usuario_logado
from app.db import Base, engine, get_db
from app.models import Unidade
from app.services.consumo import calcular_consumo
from app.services.painel import calcular_painel
from app.services.rateio import gerar_analise

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Equatorial Solar — TBG Mídia")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-troque-em-producao"),
)

templates = Jinja2Templates(directory="app/templates")

PRIORIDADE_CLASSE = {
    "🔴 CRÍTICO": "critico",
    "🟠 ALTO": "alto",
    "🟡 MÉDIO": "medio",
    "🟢 BAIXO": "baixo",
}


def _com_classe(analise):
    for a in analise:
        a["prioridade_classe"] = PRIORIDADE_CLASSE.get(a["prioridade"], "")
    return analise


# ── Autenticação ─────────────────────────────────────────────────────────

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.get("/auth/login")
async def auth_login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    request.session["user"] = {
        "email": userinfo.get("email", ""),
        "nome": userinfo.get("name", ""),
    }
    if userinfo.get("email", "").lower() not in ALLOWED_EMAILS:
        return RedirectResponse(url="/sem-acesso")
    return RedirectResponse(url="/")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


@app.get("/sem-acesso")
def sem_acesso(request: Request):
    user = usuario_logado(request) or {}
    return templates.TemplateResponse(request, "sem_acesso.html", {"email": user.get("email", "?")})


# ── Páginas ──────────────────────────────────────────────────────────────

@app.get("/")
def painel(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    dados = calcular_painel(db)
    dados.update({
        "user": usuario_logado(request),
        "active": "painel",
        "total_unidades": db.query(Unidade).count(),
    })
    return templates.TemplateResponse(request, "painel.html", dados)


@app.get("/consumo")
def consumo(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    dados = calcular_consumo(db)
    dados.update({"user": usuario_logado(request), "active": "consumo"})
    return templates.TemplateResponse(request, "consumo.html", dados)


@app.get("/rateio")
def rateio(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    analise, ultimo_mes = gerar_analise(db)
    return templates.TemplateResponse(request, "rateio.html", {
        "user": usuario_logado(request),
        "active": "rateio",
        "analise": _com_classe(analise),
        "ultimo_mes": ultimo_mes.strftime("%m/%Y") if ultimo_mes else "—",
        "agora": datetime.now().strftime("%d/%m/%Y %H:%M"),
    })


@app.get("/alertas")
def alertas(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    analise, _ = gerar_analise(db)
    return templates.TemplateResponse(request, "alertas.html", {
        "user": usuario_logado(request),
        "active": "alertas",
        "analise": _com_classe(analise),
    })
