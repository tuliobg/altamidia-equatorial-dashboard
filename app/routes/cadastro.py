from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.auth import exigir_login, usuario_logado
from app.db import get_db
from app.models import Unidade, UnidadeCodigo
from app.templating import templates

router = APIRouter(prefix="/cadastro")

STATUS_OPCOES = ["Ativa", "Desativada", "Fora do rateio"]


@router.get("")
def listar(request: Request, db: Session = Depends(get_db), status: str = "Todas"):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    query = db.query(Unidade)
    if status in STATUS_OPCOES:
        query = query.filter(Unidade.status == status)
    unidades = query.order_by(Unidade.status, Unidade.nome).all()
    return templates.TemplateResponse(request, "cadastro_lista.html", {
        "user": usuario_logado(request),
        "active": "cadastro",
        "unidades": unidades,
        "status_opcoes": STATUS_OPCOES,
        "status_atual": status,
    })


@router.get("/nova")
def form_nova(request: Request):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    return templates.TemplateResponse(request, "cadastro_form.html", {
        "user": usuario_logado(request),
        "active": "cadastro",
        "unidade": None,
        "status_opcoes": STATUS_OPCOES,
        "codigos_texto": "",
    })


@router.get("/{unidade_id}/editar")
def form_editar(unidade_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    unidade = db.get(Unidade, unidade_id)
    codigos_texto = "\n".join(c.codigo for c in unidade.codigos) if unidade else ""
    return templates.TemplateResponse(request, "cadastro_form.html", {
        "user": usuario_logado(request),
        "active": "cadastro",
        "unidade": unidade,
        "status_opcoes": STATUS_OPCOES,
        "codigos_texto": codigos_texto,
    })


@router.post("/nova")
def criar(
    request: Request,
    db: Session = Depends(get_db),
    nome: str = Form(...),
    tipo: str = Form(""),
    status: str = Form("Ativa"),
    geradora: bool = Form(False),
    pct_rateio_atual: float = Form(0.0),
    pct_rateio_sugerido: float = Form(0.0),
    codigos: str = Form(""),
):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    u = Unidade(
        nome=nome.strip(), tipo=tipo or None, status=status,
        geradora=geradora,
        pct_rateio_atual=pct_rateio_atual / 100.0,
        pct_rateio_sugerido=pct_rateio_sugerido / 100.0,
    )
    db.add(u)
    db.flush()
    _atualizar_codigos(db, u, codigos)
    db.commit()
    return RedirectResponse(url="/cadastro", status_code=303)


@router.post("/{unidade_id}/editar")
def editar(
    unidade_id: int,
    request: Request,
    db: Session = Depends(get_db),
    nome: str = Form(...),
    tipo: str = Form(""),
    status: str = Form("Ativa"),
    geradora: bool = Form(False),
    pct_rateio_atual: float = Form(0.0),
    pct_rateio_sugerido: float = Form(0.0),
    codigos: str = Form(""),
):
    redirect = exigir_login(request)
    if redirect:
        return redirect
    u = db.get(Unidade, unidade_id)
    u.nome = nome.strip()
    u.tipo = tipo or None
    u.status = status
    u.geradora = geradora
    u.pct_rateio_atual = pct_rateio_atual / 100.0
    u.pct_rateio_sugerido = pct_rateio_sugerido / 100.0
    _atualizar_codigos(db, u, codigos)
    db.commit()
    return RedirectResponse(url="/cadastro", status_code=303)


def _atualizar_codigos(db: Session, unidade: Unidade, codigos_texto: str):
    novos = {c.strip() for c in codigos_texto.replace(",", "\n").splitlines() if c.strip()}
    atuais = {c.codigo for c in unidade.codigos}
    for c in unidade.codigos[:]:
        if c.codigo not in novos:
            db.delete(c)
    for codigo in novos - atuais:
        db.add(UnidadeCodigo(unidade_id=unidade.id, codigo=codigo))
