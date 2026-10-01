FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8000
# --proxy-headers + --forwarded-allow-ips='*': o Railway termina o HTTPS na borda
# e encaminha pro container em HTTP puro, sinalizando o esquema original via
# X-Forwarded-Proto. Sem isso o Uvicorn monta o redirect_uri do OAuth como
# http://, que não bate com o https:// cadastrado no Google (erro
# redirect_uri_mismatch).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
