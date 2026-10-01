from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from app.auth import exigir_admin
from app.ctx import ctx_base
from app.db import get_db
from app.models import Usuario
from app.templating import templates

router = APIRouter(prefix="/usuarios")

PAPEIS = ["admin", "leitura"]


@router.get("")
def listar(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect
    usuarios_lista = db.query(Usuario).order_by(Usuario.papel, Usuario.email).all()
    ctx = ctx_base(request, db, "usuarios")
    ctx.update({"usuarios": usuarios_lista, "papeis": PAPEIS})
    return templates.TemplateResponse(request, "usuarios_lista.html", ctx)


@router.post("/novo")
def criar(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    nome: str = Form(""),
    papel: str = Form("leitura"),
):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect
    email = email.strip().lower()
    if papel not in PAPEIS:
        papel = "leitura"
    existente = db.query(Usuario).filter(Usuario.email == email).first()
    if existente:
        existente.papel = papel
        existente.nome = nome.strip() or existente.nome
        existente.ativo = True
    else:
        db.add(Usuario(email=email, nome=nome.strip() or None, papel=papel, ativo=True))
    db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)


@router.post("/{usuario_id}/papel")
def mudar_papel(usuario_id: int, request: Request, db: Session = Depends(get_db), papel: str = Form(...)):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect
    if papel in PAPEIS:
        u = db.get(Usuario, usuario_id)
        if u:
            u.papel = papel
            db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)


@router.post("/{usuario_id}/alternar-ativo")
def alternar_ativo(usuario_id: int, request: Request, db: Session = Depends(get_db)):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect
    u = db.get(Usuario, usuario_id)
    if u:
        # Impede que o próprio admin logado se desative por engano e perca acesso.
        sess_email = (request.session.get("user") or {}).get("email", "").lower()
        if u.email == sess_email:
            return RedirectResponse(url="/usuarios", status_code=303)
        u.ativo = not u.ativo
        db.commit()
    return RedirectResponse(url="/usuarios", status_code=303)
