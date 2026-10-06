from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from starlette.datastructures import UploadFile
from sqlalchemy.orm import Session

from app.auth import exigir_admin, usuario_logado
from app.ctx import ctx_base
from app.db import get_db
from app.models import Fatura, ImportacaoLog, Unidade, UnidadeCodigo
from app.services.extracao import extrair_dados_fatura, extrair_texto
from app.templating import templates

router = APIRouter(prefix="/faturas")

HISTORICO_LIMITE = 200


def _mes_ref_para_data(mes_ref: str) -> Optional[date]:
    try:
        mes, ano = mes_ref.split("/")
        return date(int(ano), int(mes), 1)
    except (ValueError, AttributeError):
        return None


def _encontrar_unidade(db: Session, codigo: str) -> Optional[Unidade]:
    if not codigo:
        return None
    uc = db.query(UnidadeCodigo).filter(UnidadeCodigo.codigo == codigo).first()
    return uc.unidade if uc else None


def _historico(db: Session):
    return (
        db.query(ImportacaoLog)
        .order_by(ImportacaoLog.criado_em.desc())
        .limit(HISTORICO_LIMITE)
        .all()
    )


@router.get("/upload")
def form_upload(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect
    ctx = ctx_base(request, db, "upload")
    ctx.update({"resultados": None, "historico": _historico(db)})
    return templates.TemplateResponse(request, "faturas_upload.html", ctx)


@router.post("/upload")
async def processar_upload(request: Request, db: Session = Depends(get_db)):
    redirect = exigir_admin(request, db)
    if redirect:
        return redirect

    form = await request.form()
    arquivos = form.getlist("arquivos")
    usuario = usuario_logado(request) or {}
    usuario_email = usuario.get("email")

    def _logar(arquivo_nome, status, detalhe, unidade_nome=None, mes_ref=None):
        resultados.append({"arquivo": arquivo_nome, "status": status, "detalhe": detalhe})
        db.add(ImportacaoLog(
            usuario_email=usuario_email, arquivo=arquivo_nome, unidade_nome=unidade_nome,
            mes_ref=mes_ref, status=status, detalhe=detalhe,
        ))

    resultados = []
    for arquivo in arquivos:
        if not isinstance(arquivo, UploadFile) or not arquivo.filename:
            continue
        try:
            conteudo = await arquivo.read()
            import io
            texto = extrair_texto(io.BytesIO(conteudo))
            dados = extrair_dados_fatura(texto)
        except Exception as e:
            _logar(arquivo.filename, "erro", f"Não foi possível ler o PDF ({e})")
            continue

        if not dados["mes_ref"]:
            _logar(arquivo.filename, "erro", "Não consegui identificar o mês de referência na fatura.")
            continue

        unidade = _encontrar_unidade(db, dados["codigo"])
        if not unidade:
            _logar(arquivo.filename, "erro",
                   f"Código de UC '{dados['codigo']}' não está cadastrado em nenhuma unidade. "
                   f"Cadastre o código em /cadastro antes de reenviar.",
                   mes_ref=dados["mes_ref"])
            continue

        ano_mes = _mes_ref_para_data(dados["mes_ref"])
        existente = db.query(Fatura).filter_by(unidade_id=unidade.id, ano_mes=ano_mes).first()
        acao = "atualizada" if existente else "criada"
        f = existente or Fatura(unidade_id=unidade.id, ano_mes=ano_mes)
        f.kwh_tax = dados["kwh_tax"]
        f.cip_tax = dados["cip_tax"]
        f.real_consumo = dados["real_consumo"]
        f.energia_injetada = dados["energia_injetada"]
        f.diferenca_kw = dados["diferenca_kw"]
        f.real_valor = dados["real_valor"]
        f.pago = dados["pago"]
        f.diferenca = dados["diferenca"]
        if dados["acumulado"]:
            f.acumulado = dados["acumulado"]
        if dados["a_expirar"]:
            f.a_expirar = dados["a_expirar"]
            f.a_expirar_ref = dados["a_expirar_ref"]
        if not existente:
            db.add(f)

        _logar(
            arquivo.filename, acao,
            f"{unidade.nome} — {dados['mes_ref']} — consumo {dados['real_consumo']:.0f} kWh, "
            f"custo sem solar R$ {dados['real_valor']:.2f}, pago R$ {dados['pago']:.2f}",
            unidade_nome=unidade.nome, mes_ref=dados["mes_ref"],
        )

    db.commit()

    ctx = ctx_base(request, db, "upload")
    ctx.update({"resultados": resultados, "historico": _historico(db)})
    return templates.TemplateResponse(request, "faturas_upload.html", ctx)
