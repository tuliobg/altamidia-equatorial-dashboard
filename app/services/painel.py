"""
Réplica das fórmulas da aba Painel da planilha original (amortização do
investimento solar). Ver planilha original, aba Painel, células B5:E10.
"""

import math
from datetime import date
from calendar import monthrange
from sqlalchemy.orm import Session

from app.models import Fatura, Investimento


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, 1)


def calcular_painel(db: Session):
    investimentos = db.query(Investimento).all()
    investimento_total = sum(
        i.valor for i in investimentos if "não amortizado" not in i.descricao.lower()
    )

    todas_faturas = db.query(Fatura).all()
    economia_acumulada = sum(f.diferenca for f in todas_faturas)

    ultimo_mes_row = (
        db.query(Fatura.ano_mes)
        .filter(Fatura.real_consumo > 0)
        .order_by(Fatura.ano_mes.desc())
        .first()
    )
    ultimo_mes = ultimo_mes_row[0] if ultimo_mes_row else date.today()

    inicio_12m = _add_months(ultimo_mes, -11)
    faturas_12m = [f for f in todas_faturas if inicio_12m <= f.ano_mes <= ultimo_mes]
    economia_media_mes = sum(f.diferenca for f in faturas_12m) / 12

    falta_amortizar = investimento_total - economia_acumulada
    pct_amortizado = (economia_acumulada / investimento_total) if investimento_total else 0.0
    payback_meses = 0 if falta_amortizar <= 0 else math.ceil(falta_amortizar / economia_media_mes) if economia_media_mes > 0 else None

    # Histórico dos últimos 24 meses para o gráfico
    historico = []
    acumulado_corrente = 0.0
    mes_cursor = _add_months(ultimo_mes, -23)
    # soma acumulada ATÉ o início da janela (para o primeiro ponto do gráfico já
    # refletir a economia acumulada real, não zerada)
    acumulado_corrente = sum(f.diferenca for f in todas_faturas if f.ano_mes < mes_cursor)

    for _ in range(24):
        do_mes = [f for f in todas_faturas if f.ano_mes == mes_cursor]
        custo_sem_solar = sum(f.real_valor for f in do_mes)
        pago = sum(f.pago for f in do_mes)
        economia = custo_sem_solar - pago
        acumulado_corrente += economia
        historico.append({
            "mes": mes_cursor.strftime("%b/%y"),
            "custo_sem_solar": round(custo_sem_solar, 2),
            "pago": round(pago, 2),
            "economia_acumulada": round(acumulado_corrente, 2),
        })
        mes_cursor = _add_months(mes_cursor, 1)

    return {
        "investimento_total": investimento_total,
        "economia_acumulada": economia_acumulada,
        "pct_amortizado": pct_amortizado,
        "falta_amortizar": falta_amortizar,
        "economia_media_mes": economia_media_mes,
        "payback_meses": payback_meses if payback_meses is not None else "—",
        "ultimo_mes": ultimo_mes.strftime("%m/%Y"),
        "historico": historico,
    }
