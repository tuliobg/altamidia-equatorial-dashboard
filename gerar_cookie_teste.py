import json
from base64 import b64encode
import itsdangerous

signer = itsdangerous.TimestampSigner("dev-secret-troque-em-producao")
data = {"user": {"email": "diretoria@altamidia.com"}}
print(signer.sign(b64encode(json.dumps(data).encode())).decode())
