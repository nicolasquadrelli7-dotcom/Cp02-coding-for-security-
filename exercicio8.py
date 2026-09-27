"""
Exercício 8 - API de triagem com RandomForest e auditoria.
"""

import os
from datetime import datetime
import numpy as np
from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
from sklearn.model_selection import train_test_split

app = Flask(__name__)

X = np.array([
    [0, 1, 1200, 14],
    [1, 2, 2500, 13],
    [0, 1, 1800, 9],
    [2, 2, 5000, 10],
    [1, 3, 7000, 15],
    [0, 2, 3000, 8],
    [2, 4, 10000, 12],
    [3, 5, 15000, 2],
    [5, 6, 25000, 1],
    [8, 7, 45000, 3],
    [12, 7, 90000, 3],
    [10, 8, 85000, 4],
    [15, 9, 120000, 2],
    [9, 10, 100000, 1],
    [6, 8, 70000, 5],
    [0, 1, 1200, 14],
    [1, 1, 2000, 11],
    [4, 6, 30000, 2],
    [7, 7, 60000, 3],
    [2, 3, 8000, 16],
])

y = np.array([
    0, 0, 0, 0, 0, 0, 0, 1, 1, 1,
    1, 1, 1, 1, 1, 0, 0, 1, 1, 0
])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y
)

modelo = RandomForestClassifier(
    n_estimators=150,
    random_state=42,
    class_weight="balanced",
)
modelo.fit(X_train, y_train)

mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = mongo[os.getenv("MONGO_DATABASE", "seguranca")]
previsoes = db["previsoes"]


@app.route("/api/triagem", methods=["POST"])
def triagem():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict) or "features" not in dados:
        return jsonify({"erro": "corpo JSON deve conter 'features'"}), 400

    features = dados["features"]

    if not isinstance(features, list):
        return jsonify({"erro": "features devem ser uma lista"}), 400

    if len(features) != 4:
        return jsonify({
            "erro": f"esperadas 4 features, recebidas {len(features)}"
        }), 400

    if any(isinstance(valor, bool) or not isinstance(valor, (int, float)) for valor in features):
        return jsonify({"erro": "features devem ser numéricas"}), 400

    entrada = np.array(features, dtype=float).reshape(1, -1)
    classe = int(modelo.predict(entrada)[0])
    probabilidades = modelo.predict_proba(entrada)[0]
    confianca = float(max(probabilidades))
    risco = "alto" if classe == 1 else "baixo"

    previsoes.insert_one({
        "entrada": features,
        "saida": risco,
        "confianca": confianca,
        "timestamp": datetime.utcnow(),
    })

    return jsonify({"risco": risco, "confianca": round(confianca, 2)}), 200


@app.route("/api/modelo/metricas", methods=["GET"])
def metricas():
    pred = modelo.predict(X_test)

    return jsonify({
        "precisao": round(float(precision_score(y_test, pred, zero_division=0)), 2),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 2),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 2),
        "matriz": confusion_matrix(y_test, pred).tolist(),
        "aviso": "A acurácia foi omitida de propósito porque, sozinha, pode esconder desequilíbrio entre as classes; precisão, recall, F1 e a matriz mostram melhor os erros de classificação.",
    }), 200


if __name__ == "__main__":
    previsoes.delete_many({})
    app.run(debug=False, host="127.0.0.1", port=5008)
