"""Smoke test: renderiza as 4 páginas com uma sessão forjada (sem depender
de credenciais reais do Google OAuth) e confere que nenhuma quebra."""
import json
from base64 import b64encode

import itsdangerous
from fastapi.testclient import TestClient

from app.main import app

SECRET = "dev-secret-troque-em-producao"
signer = itsdangerous.TimestampSigner(SECRET)
session_data = {"user": {"email": "diretoria@altamidia.com", "nome": "Teste"}}
cookie_value = signer.sign(b64encode(json.dumps(session_data).encode())).decode()

client = TestClient(app)
client.cookies.set("session", cookie_value)

for path in ["/", "/consumo", "/rateio", "/alertas"]:
    resp = client.get(path)
    status = "OK" if resp.status_code == 200 else f"FALHOU ({resp.status_code})"
    print(f"{path:<12} {status}")
    if resp.status_code != 200:
        print(resp.text[:2000])
