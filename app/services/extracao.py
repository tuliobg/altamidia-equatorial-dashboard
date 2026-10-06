"""
Extração de dados de fatura PDF da Equatorial Alagoas — porte de
Agente Equatorial/orquestrador_mensal.py::extrair_dados_pdf() (já validado
contra centenas de faturas reais). Ver também Agente Equatorial/README.md
para o histórico de por que REAL_VALOR e PAGO são coisas diferentes.
"""

import re

import pdfplumber

REGEX_SALDO = re.compile(r"Saldo Acumulado Geral Total[:\s]+([\d\.,]+)", re.IGNORECASE)
REGEX_EXPIRAR = re.compile(
    r"[Ss]aldo.{0,40}[Aa] [Ee]xpirar[^\d]*([\d\.,]+)(?:\s*na\s+ref\s+(\d{2})/(\d{2}))?"
)


def _num(s):
    if not s or s == "0":
        return 0.0
    s = s.strip().rstrip(".,")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def extrair_texto(caminho_ou_arquivo) -> str:
    texto = ""
    with pdfplumber.open(caminho_ou_arquivo) as pdf:
        for page in pdf.pages[:3]:
            t = page.extract_text()
            if t:
                texto += t + "\n"
    return texto


def extrair_dados_fatura(texto: str) -> dict:
    def buscar(pattern, default="0"):
        m = re.search(pattern, texto, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else default

    # Mês de referência
    mes_ref = buscar(r'(?:Conta\s+M[êe]s|Compet[êe]ncia)[^\d]*(\d{2}/\d{4})', "")
    if not mes_ref:
        mes_ref = buscar(r'(\d{2}/\d{4})\s+\d{2}/\d{2}/\d{4}\s+R\$', "")

    # Consumo real (kWh)
    consumo_str = buscar(r'Consumo\s+ATIVO\s+TOTAL\s+[\d\.]+\s+[\d\.]+\s+[\d,]+\s+([\d\.]+)\s+kWh')
    if consumo_str == "0":
        consumo_str = buscar(r'ATIVO\s+TOTAL\s+[\d\.]+\s+[\d\.]+\s+1,00\s+([\d\.]+)\s+kWh')
    consumo_kwh = int(consumo_str.replace(".", "")) if consumo_str.replace(".", "").isdigit() else _num(consumo_str)

    # Compensado (soma todas as linhas)
    compensados = re.findall(r'Consumo\s+Compensado\s*\(kWh\)\s+([\d\.,]+)', texto, re.IGNORECASE)
    compensado_kwh = sum(_num(v) for v in compensados)

    # Total a pagar (boleto — valor líquido, já com desconto solar)
    total_rs = buscar(r'\d{2}/\d{4}\s+\d{2}/\d{2}/\d{4}\s+R\$\s*([\d\.,]+)')
    if total_rs == "0":
        total_rs = buscar(r'\d+\s+R\$\s+([\d]+[\.,]\d{2})\b')
    if total_rs == "0":
        total_rs = buscar(r'Total\s+a\s+Pagar\s+R\$\s*([\d\.,]+)')

    # Tarifa kWh (com tributos)
    tarifa_kwh = buscar(r'Consumo\s*\(kWh\)\s+[\d\.,]+\s+([\d,]+)\s+[\d,]+')
    if tarifa_kwh == "0":
        tarifa_kwh = buscar(r'Consumo\s*\(kWh\)[^\n]*?([\d]+,[\d]+)\s+[\d]+,[\d]+\s+[\d]+,[\d]+')

    # CIP
    cip_rs = buscar(r'Cip[- ]Ilum[^\n]*?([\d\.,]+)')

    # Código da conta / UC — cuidado: o corpo da fatura pode citar o código de
    # OUTRA UC (ex: "recebe excedente ... das seguintes UCs: 1.524.625.008-00"
    # referenciando a geradora). Por isso usamos âncoras específicas do próprio
    # código da conta, nunca um regex genérico solto no texto inteiro.
    codigo = buscar(r'(?:Conta\s+Contrato|C\.C\.|Conta\s+Contrato:)\s*(\d{7,12})')
    if codigo == "0":
        # Formato antigo: "INSTALAÇÃO: 7006624" / "Conta Contrato\n3000686327"
        codigo = buscar(r'Chave de Acesso em:\s*\n?\s*(\d{7,12})\s+https')
    if codigo == "0":
        # Formato novo ANEEL, logo antes do link de consulta da NF3e
        codigo = buscar(r'Chave de Acesso em:\s*\n?\s*([\d]{1,3}(?:\.\d{3}){2,3}-\d{2})\s+https')
    if codigo == "0":
        # Rodapé do boleto: "...DISTRIB. DE ENERGIA S.A. <codigo> MM/AAAA"
        codigo = buscar(r'DISTRIB\.\s*DE\s*ENERGIA\s*S\.A\.\s+([\d.\-]{7,18})\s+\d{2}/\d{4}')

    # Acúmulo e a expirar (quando a unidade já tem saldo de mini/microgeração)
    m_saldo = REGEX_SALDO.search(texto)
    acumulado = _num(m_saldo.group(1)) if m_saldo else 0.0
    m_expirar = REGEX_EXPIRAR.search(texto)
    a_expirar = _num(m_expirar.group(1)) if m_expirar else 0.0
    a_expirar_ref = (
        f"{m_expirar.group(2)}/20{m_expirar.group(3)}"
        if m_expirar and m_expirar.group(2)
        else None
    )

    consumo_kwh = float(consumo_kwh)
    tarifa_kwh_f = _num(tarifa_kwh)
    cip_rs_f = _num(cip_rs)
    pago_rs = _num(total_rs)
    real_valor = consumo_kwh * tarifa_kwh_f + cip_rs_f

    return {
        "mes_ref": mes_ref,
        "codigo": codigo,
        "real_consumo": consumo_kwh,
        "energia_injetada": round(compensado_kwh, 2),
        "diferenca_kw": round(consumo_kwh - compensado_kwh, 2),
        "kwh_tax": tarifa_kwh_f,
        "cip_tax": cip_rs_f,
        "acumulado": acumulado,
        "a_expirar": a_expirar,
        "a_expirar_ref": a_expirar_ref,
        "real_valor": round(real_valor, 2),
        "pago": pago_rs,
        "diferenca": round(real_valor - pago_rs, 2),
    }
