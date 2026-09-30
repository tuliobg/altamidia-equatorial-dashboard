"""
Adiciona os códigos novos (formato ANEEL, vigentes desde 01/04/2026) às
unidades já migradas — recuperados de Meu Drive/4.8 EQUATORIAL/Logs/
relatorio_2026_08.txt (tabela código-antigo -> código-novo confirmada
contra faturas reais).
"""
from app.db import SessionLocal
from app.models import Unidade, UnidadeCodigo

CODIGOS_NOVOS = {
    "Avenue Center": "608.820.008-50",
    "Cond.Navegantes": "1.261.087.008-31",
    "Front Cruz das Almas": "1.521.987.008-03",
    "Front Fernandes Lima": "1.554.357.008-85",
    "Front Maceio Shopping": "1.455.304.008-17",
    "Galpao- Novo": "1.300.501.008-52",
    "LED- Lopes Imobiliaria": "1.626.379.008-33",
    "LED - Norcom": "1.557.627.008-48",
    "LED - Permanente01": "1.627.585.008-64",
    "LED - Posto Tigre": "1.557.060.008-00",
    "Villas Manatee": "1.545.021.008-86",
}

db = SessionLocal()
for nome, codigo in CODIGOS_NOVOS.items():
    u = db.query(Unidade).filter_by(nome=nome).first()
    if not u:
        print(f"⚠️  Unidade não encontrada: {nome}")
        continue
    ja_tem = any(c.codigo == codigo for c in u.codigos)
    if ja_tem:
        print(f"— {nome}: já tinha {codigo}")
        continue
    db.add(UnidadeCodigo(unidade_id=u.id, codigo=codigo))
    print(f"✅ {nome}: adicionado {codigo}")

db.commit()
