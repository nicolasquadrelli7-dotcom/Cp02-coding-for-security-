"""
Exercício 9 - Rate limiting guiado por anomalia.

Para testar IPs diferentes localmente:
    $env:LAB_MODE="1"

Nesse modo, somente requisições locais podem usar X-Test-IP para simular o IP.
"""

import os
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest

app = Flask(__name__)

mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = mongo[os.getenv("MONGO_DATABASE", "seguranca")]
acessos = db["acessos"]

ips_bloqueados = set()


def ip_cliente():
    ip = request.remote_addr or "desconhecido"
    if os.getenv("LAB_MODE", "0") == "1" and ip in {"127.0.0.1", "::1"}:
        ip_teste = request.headers.get("X-Test-IP")
        if ip_teste:
            return ip_teste
    return ip


def analisar_ips():
    agora = datetime.utcnow()
    inicio = agora - timedelta(minutes=10)

    pipeline = [
        {"$match": {"timestamp": {"$gte": inicio}}},
        {"$group": {
            "_id": "$ip",
            "total": {"$sum": 1},
            "erros_4xx": {
                "$sum": {
                    "$cond": [
                        {"$and": [
                            {"$gte": ["$status", 400]},
                            {"$lt": ["$status", 500]},
                        ]},
                        1,
                        0,
                    ]
                }
            },
            "rotas_distintas": {"$addToSet": "$rota"},
        }},
        {"$project": {
            "_id": 1,
            "req_por_minuto": {"$divide": ["$total", 10]},
            "taxa_4xx": {
                "$cond": [
                    {"$eq": ["$total", 0]},
                    0,
                    {"$divide": ["$erros_4xx", "$total"]},
                ]
            },
            "rotas_distintas": {"$size": "$rotas_distintas"},
        }},
    ]

    dados = list(acessos.aggregate(pipeline))

    if len(dados) < 2:
        return dados

    X = [
        [d["req_por_minuto"], d["taxa_4xx"], d["rotas_distintas"]]
        for d in dados
    ]

    modelo = IsolationForest(
        contamination=0.2,
        random_state=42,
    )
    previsoes = modelo.fit_predict(X)

    for item, previsao in zip(dados, previsoes):
        item["anomalia"] = previsao == -1
        if previsao == -1:
            ips_bloqueados.add(item["_id"])

    return dados


@app.before_request
def registrar_request():
    ip = ip_cliente()

    if ip in ips_bloqueados:
        request._bloqueado_anomalia = True
        return jsonify({"erro": "muitas requisições"}), 429

    request._log_id = acessos.insert_one({
        "ip": ip,
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.utcnow(),
    }).inserted_id


@app.after_request
def completar_log(response):
    log_id = getattr(request, "_log_id", None)
    if log_id is not None:
        acessos.update_one(
            {"_id": log_id},
            {"$set": {"status": response.status_code}},
        )

    if response.status_code == 429:
        response.headers["Retry-After"] = "60"

    return response


@app.route("/")
def home():
    return jsonify({"status": "ok"}), 200


@app.route("/api/status")
def status():
    return jsonify({"status": "ok"}), 200


@app.route("/analisar")
def analisar():
    dados = analisar_ips()
    resposta = []

    for item in dados:
        resposta.append({
            "ip": item["_id"],
            "req_por_minuto": round(item["req_por_minuto"], 2),
            "taxa_4xx": round(item["taxa_4xx"], 2),
            "rotas_distintas": item["rotas_distintas"],
            "resultado": "ANOMALIA -> bloqueado" if item.get("anomalia") else "normal",
        })

    return jsonify(resposta), 200


if __name__ == "__main__":
    acessos.delete_many({})
    ips_bloqueados.clear()
    app.run(debug=False, host="127.0.0.1", port=5009)
