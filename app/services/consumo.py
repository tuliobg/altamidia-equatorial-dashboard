from datetime import date
from sqlalchemy.orm import Session

from app.models import Fatura, Unidade
from app.services.painel import _add_months

FRANQUIA_KWH = 12500.0


def calcular_consumo(db: Session):
    todas_faturas = db.query(Fatura).all()
    ultimo_mes_row = (
        db.query(Fatura.ano_mes)
        .filter(Fatura.real_consumo > 0)
        .order_by(Fatura.ano_mes.desc())
        .first()
    )
    ultimo_mes = ultimo_mes_row[0] if ultimo_mes_row else date.today()
    inicio = _add_months(ultimo_mes, -11)

    meses, consumo_total = [], []
    cursor = inicio
    for _ in range(12):
        total = sum(f.real_consumo for f in todas_faturas if f.ano_mes == cursor)
        meses.append(cursor.strftime("%b/%y"))
        consumo_total.append(round(total, 1))
        cursor = _add_months(cursor, 1)

    unidades_ativas = db.query(Unidade).filter(
        Unidade.status == "Ativa", Unidade.geradora == False  # noqa: E712
    ).all()

    linhas = []
    for u in unidades_ativas:
        faturas_12m = [f for f in u.faturas if inicio <= f.ano_mes <= ultimo_mes]
        consumo_medio = sum(f.real_consumo for f in faturas_12m) / len(faturas_12m) if faturas_12m else 0.0
        linhas.append({
            "nome": u.nome,
            "consumo_medio": consumo_medio,
            "pct_atual": u.pct_rateio_atual,
            "kwh_alocado": u.pct_rateio_atual * FRANQUIA_KWH,
        })
    linhas.sort(key=lambda l: -l["consumo_medio"])

    return {"meses": meses, "consumo_total": consumo_total, "unidades": linhas}
