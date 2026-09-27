"""
Exercício 5 - ORDER BY seguro com whitelist.
"""

import os
from datetime import datetime
from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

COLUNAS = {
    "data": "criado_em",
    "sev": "severidade",
    "ip": "ip_origem",
}

ORDEM = {
    "asc": "ASC",
    "desc": "DESC",
}


def mysql_config():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "seguranca"),
    }


def preparar_banco():
    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tipo VARCHAR(50) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            ip_origem VARCHAR(45) NOT NULL,
            criado_em DATETIME NOT NULL
        )
    """)
    cur.execute("SELECT COUNT(*) FROM eventos")
    if cur.fetchone()[0] == 0:
        dados = [
            ("LOGIN_FAIL", "critica", "10.0.0.1", datetime.now()),
            ("PORT_SCAN", "alta", "10.0.0.2", datetime.now()),
            ("XSS", "media", "10.0.0.3", datetime.now()),
            ("BRUTE_FORCE", "critica", "10.0.0.4", datetime.now()),
            ("MALWARE", "alta", "10.0.0.5", datetime.now()),
            ("AUTH_FAIL", "baixa", "10.0.0.6", datetime.now()),
        ]
        cur.executemany(
            "INSERT INTO eventos (tipo,severidade,ip_origem,criado_em) VALUES (%s,%s,%s,%s)",
            dados,
        )
    con.commit()
    cur.close()
    con.close()


@app.route("/api/eventos", methods=["GET"])
def listar_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "asc")
    tamanho_raw = request.args.get("tamanho", "10")

    if ordenar_por not in COLUNAS:
        return jsonify({"erro": "campo de ordenação inválido"}), 400

    if ordem not in ORDEM:
        return jsonify({"erro": "ordem inválida"}), 400

    try:
        tamanho = int(tamanho_raw)
    except ValueError:
        return jsonify({"erro": "tamanho deve ser inteiro"}), 400

    if tamanho < 1:
        return jsonify({"erro": "tamanho deve ser maior que zero"}), 400

    tamanho = min(tamanho, 100)

    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)

    # LIMIT aceita valor como dado parametrizado.
    # ORDER BY não aceita nome de coluna como dado parametrizado.
    # Por isso identificadores precisam vir de uma whitelist fechada.
    query = (
        "SELECT id,tipo,severidade,ip_origem,criado_em "
        f"FROM eventos ORDER BY {COLUNAS[ordenar_por]} {ORDEM[ordem]} LIMIT %s"
    )

    try:
        cur.execute(query, (tamanho,))
        dados = cur.fetchall()
        return jsonify(dados), 200
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    preparar_banco()
    app.run(debug=False, host="127.0.0.1", port=5005)
