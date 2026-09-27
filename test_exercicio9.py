"""
Teste local do exercício 9.

Execute o servidor com:
    PowerShell: $env:LAB_MODE="1"; python exercicio9.py

Depois, em outro terminal:
    python test_exercicio9.py
"""

import time
import requests

BASE = "http://127.0.0.1:5009"
NORMAL = "192.168.1.10"
HOSTIL = "185.220.101.1"

# 5 requisições válidas do IP normal.
for _ in range(5):
    r = requests.get(BASE + "/api/status", headers={"X-Test-IP": NORMAL})
    print("normal:", r.status_code)
    time.sleep(0.2)

# 60 requisições em cerca de 10 segundos; 40 são rotas inexistentes.
for i in range(60):
    rota = "/rota-inexistente-" + str(i % 40) if i < 40 else "/api/status"
    r = requests.get(BASE + rota, headers={"X-Test-IP": HOSTIL})
    if i % 10 == 0:
        print("hostil:", i + 1, r.status_code)
    time.sleep(0.05)

analise = requests.get(BASE + "/analisar", headers={"X-Test-IP": NORMAL})
print("=== Análise de acessos ===")
print(analise.json())

# Após a análise, o IP anômalo deve receber 429.
r = requests.get(BASE + "/api/status", headers={"X-Test-IP": HOSTIL})
print("próxima requisição do hostil:", r.status_code, r.json(), r.headers.get("Retry-After"))
