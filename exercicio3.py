"""
Exercício 3 - Retenção TTL e janela temporal.
"""

import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient


def main():
    random.seed(42)

    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    db = client[os.getenv("MONGO_DATABASE", "seguranca")]
    eventos = db["eventos"]

    eventos.delete_many({})
    eventos.create_index("timestamp", expireAfterSeconds=604800, name="ttl_7_dias")

    agora = datetime.utcnow()
    tipos = ["AUTH_FAIL", "PORT_SCAN", "XSS", "BRUTE_FORCE"]

    documentos = []
    for _ in range(200):
        timestamp = agora - timedelta(
            hours=random.uniform(0, 24),
            minutes=random.uniform(0, 59),
        )
        documentos.append({
            "tipo": random.choice(tipos),
            "falha": True,
            "timestamp": timestamp,
        })

    eventos.insert_many(documentos)

    pipeline = [
        {"$match": {"timestamp": {"$gte": agora - timedelta(hours=24)}}},
        {"$group": {
            "_id": {"$hour": "$timestamp"},
            "total": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]

    resultado = list(eventos.aggregate(pipeline))

    print("=== Falhas por hora (últimas 24h) ===")
    for item in resultado:
        print(f'{item["_id"]:02d}h | {item["total"]}')

    if resultado:
        pico = max(resultado, key=lambda item: item["total"])
        print(f'Hora de pico: {pico["_id"]:02d}h ({pico["total"]} falhas)')

    print("Índice TTL ativo: eventos com mais de 7 dias serão removidos automaticamente.")
    print("Segurança: o TTL reduz a retenção de dados que não precisam permanecer disponíveis, limitando exposição em caso de acesso indevido.")

    janela_6h = list(eventos.find({
        "timestamp": {"$gte": agora - timedelta(hours=6)}
    }))
    print(f"Eventos nas últimas 6h: {len(janela_6h)}")
    print("Observação: a limpeza do TTL do MongoDB ocorre periodicamente, não instantaneamente.")

    client.close()


if __name__ == "__main__":
    main()
