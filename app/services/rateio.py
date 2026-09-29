"""
Motor de sugestão de rateio — mesma lógica de
Agente Equatorial/motor_rateio.py (planilha), portada para ler do banco
em vez do .xlsx. Ver aquele arquivo para o racional completo de cada regra.
"""

from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Unidade, Fatura

FRANQUIA_KWH = 12500.0


def _edate(dt: datetime, meses: int) -> datetime:
    ano, mes = dt.year, dt.month + meses
    while mes <= 0:
        mes += 12
        ano -= 1
    while mes > 12:
        mes -= 12
        ano += 1
    return datetime(ano, mes, 1)


def cobertura_alvo(consumo_medio: float, acumulado: float):
    if consumo_medio <= 0:
        return None, "sem histórico"
    razao = acumulado / consumo_medio
    if razao >= 3:
        return 0.55, "🔴 acúmulo crítico"
    if razao >= 1:
        return 0.90, "🟡 acúmulo moderado"
    if razao > 0:
        return 1.05, "🟢 acúmulo baixo"
    return 1.20, "🟢 zerado / sem crédito"


def normalizar_percentuais(propostas: dict) -> dict:
    """Método dos maiores restos — garante soma = 100% exatos."""
    nomes = list(propostas.keys())
    soma = sum(propostas.values())
    if soma <= 0:
        return {n: 0.0 for n in nomes}
    pontos_exatos = {n: (propostas[n] / soma) * 100 for n in nomes}
    base = {n: int(pontos_exatos[n]) for n in nomes}
    falta = 100 - sum(base.values())
    restos = sorted(nomes, key=lambda n: pontos_exatos[n] - base[n], reverse=True)
    for n in restos[:falta]:
        base[n] += 1
    return {n: base[n] / 100 for n in nomes}


def montar_justificativa(nome, consumo_medio, meses, acumulado, a_expirar,
                          pct_atual, pct_sugerido, classe):
    if consumo_medio <= 0:
        return (f"Sem histórico de consumo suficiente ({meses} mês(es) com dados). "
                f"Mantido o % atual até haver dados consistentes.")
    kwh_sugerido = pct_sugerido * FRANQUIA_KWH
    cobertura = kwh_sugerido / consumo_medio if consumo_medio else 0
    delta_kwh = (pct_sugerido - pct_atual) * FRANQUIA_KWH

    partes = [f"Consumo médio de {consumo_medio:,.0f} kWh/mês ({meses} mês(es) com dados).".replace(",", ".")]
    if acumulado > 0:
        partes.append(f"Acúmulo atual de {acumulado:,.0f} kWh ({classe}).".replace(",", "."))
    else:
        partes.append("Sem acúmulo de créditos no momento.")
    partes.append(
        f"Alocação sugerida de {pct_sugerido:.0%} ({kwh_sugerido:,.0f} kWh) "
        f"resulta em cobertura de {cobertura:.0%}.".replace(",", ".")
    )
    if abs(delta_kwh) >= 50:
        direcao = "aumento" if delta_kwh > 0 else "redução"
        partes.append(f"Variação vs. rateio atual: {direcao} de {abs(delta_kwh):,.0f} kWh/mês.".replace(",", "."))
    if a_expirar and a_expirar > 0:
        partes.append(f"Atenção: {a_expirar:,.0f} kWh a expirar em breve.".replace(",", "."))
    return " ".join(partes)


def classificar_prioridade(delta_kwh, classe_acumulo):
    if "crítico" in classe_acumulo and delta_kwh <= 0:
        return "🔴 CRÍTICO"
    if abs(delta_kwh) >= 800:
        return "🔴 CRÍTICO"
    if abs(delta_kwh) >= 400:
        return "🟠 ALTO"
    if abs(delta_kwh) >= 150:
        return "🟡 MÉDIO"
    return "🟢 BAIXO"


def gerar_analise(db: Session):
    unidades = db.query(Unidade).filter(
        Unidade.status == "Ativa", Unidade.geradora == False  # noqa: E712
    ).all()

    ultimo_mes_global = (
        db.query(Fatura.ano_mes)
        .filter(Fatura.real_consumo > 0)
        .order_by(Fatura.ano_mes.desc())
        .first()
    )
    if not ultimo_mes_global:
        return [], None
    ultimo_mes_global = datetime.combine(ultimo_mes_global[0], datetime.min.time())
    inicio_janela = _edate(ultimo_mes_global, -11)

    analise = []
    for u in unidades:
        faturas = [
            f for f in u.faturas
            if inicio_janela <= datetime.combine(f.ano_mes, datetime.min.time()) <= ultimo_mes_global
        ]
        consumo_medio = sum(f.real_consumo for f in faturas) / len(faturas) if faturas else 0.0
        meses_com_dados = sum(1 for f in faturas if f.real_consumo > 0)

        faturas_reais = [
            f for f in u.faturas
            if datetime.combine(f.ano_mes, datetime.min.time()) <= ultimo_mes_global
        ]
        ultima = max(faturas_reais, key=lambda f: f.ano_mes) if faturas_reais else None
        acumulado = ultima.acumulado if ultima else 0.0
        a_expirar = ultima.a_expirar if ultima else 0.0

        cobertura, classe = cobertura_alvo(consumo_medio, acumulado)
        pct_bruto = u.pct_rateio_atual if cobertura is None else (consumo_medio * cobertura) / FRANQUIA_KWH

        analise.append({
            "unidade_id": u.id,
            "nome": u.nome,
            "pct_atual": u.pct_rateio_atual,
            "pct_bruto": pct_bruto,
            "consumo_medio": consumo_medio,
            "meses_com_dados": meses_com_dados,
            "acumulado": acumulado,
            "a_expirar": a_expirar,
            "classe_acumulo": classe,
        })

    pct_final = normalizar_percentuais({a["nome"]: a["pct_bruto"] for a in analise})

    for a in analise:
        a["pct_sugerido"] = pct_final[a["nome"]]
        a["delta_kwh"] = (a["pct_sugerido"] - a["pct_atual"]) * FRANQUIA_KWH
        a["prioridade"] = classificar_prioridade(a["delta_kwh"], a["classe_acumulo"])
        a["justificativa"] = montar_justificativa(
            a["nome"], a["consumo_medio"], a["meses_com_dados"],
            a["acumulado"], a["a_expirar"], a["pct_atual"], a["pct_sugerido"],
            a["classe_acumulo"],
        )

    ordem_prioridade = {"🔴 CRÍTICO": 0, "🟠 ALTO": 1, "🟡 MÉDIO": 2, "🟢 BAIXO": 3}
    analise.sort(key=lambda a: (ordem_prioridade.get(a["prioridade"], 9), -abs(a["delta_kwh"])))

    return analise, ultimo_mes_global
