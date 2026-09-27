"""
Exercício 6 - Controle de acesso por X-API-Key.
"""

import os
from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)


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
        CREATE TABLE IF NOT EXISTS analistas (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            api_key VARCHAR(100) NOT NULL UNIQUE,
            nivel INT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS incidentes (
            id INT PRIMARY KEY,
            dono_id INT NOT NULL,
            titulo VARCHAR(200) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            status VARCHAR(30) NOT NULL,
            FOREIGN KEY (dono_id) REFERENCES analistas(id)
        )
    """)
    cur.execute("DELETE FROM incidentes")
    cur.execute("DELETE FROM analistas")

    cur.executemany(
        "INSERT INTO analistas (id,nome,api_key,nivel) VALUES (%s,%s,%s,%s)",
        [
            (1, "ana", "key-ana-001", 5),
            (2, "bruno", "key-bruno-002", 2),
        ],
    )
    cur.executemany(
        "INSERT INTO incidentes (id,dono_id,titulo,severidade,status) VALUES (%s,%s,%s,%s,%s)",
        [
            (1, 1, "Brute force SSH", "critica", "aberto"),
            (2, 2, "Phishing no RH", "media", "aberto"),
        ],
    )
    con.commit()
    cur.close()
    con.close()


def autenticar():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None, (jsonify({"erro": "autenticação necessária"}), 401)

    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id,nome,nivel FROM analistas WHERE api_key = %s",
            (api_key,),
        )
        analista = cur.fetchone()
    finally:
        cur.close()
        con.close()

    if not analista:
        return None, (jsonify({"erro": "credencial inválida"}), 401)

    return analista, None


@app.route("/api/incidentes/<int:incidente_id>", methods=["GET"])
def obter_incidente(incidente_id):
    analista, erro = autenticar()
    if erro:
        return erro

    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id,dono_id,titulo,severidade,status FROM incidentes WHERE id = %s",
            (incidente_id,),
        )
        incidente = cur.fetchone()

        if not incidente:
            return jsonify({"erro": "incidente não encontrado"}), 404

        if analista["nivel"] < 5 and incidente["dono_id"] != analista["id"]:
            return jsonify({"erro": "acesso negado"}), 403

        return jsonify(incidente), 200
    finally:
        cur.close()
        con.close()


@app.route("/api/incidentes", methods=["GET"])
def listar_incidentes():
    analista, erro = autenticar()
    if erro:
        return erro

    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)
    try:
        if analista["nivel"] >= 5:
            cur.execute("SELECT id,dono_id,titulo,severidade,status FROM incidentes ORDER BY id")
        else:
            cur.execute(
                "SELECT id,dono_id,titulo,severidade,status FROM incidentes WHERE dono_id = %s ORDER BY id",
                (analista["id"],),
            )
        return jsonify(cur.fetchall()), 200
    finally:
        cur.close()
        con.close()


@app.route("/api/incidentes/<int:incidente_id>", methods=["DELETE"])
def remover_incidente(incidente_id):
    analista, erro = autenticar()
    if erro:
        return erro

    if analista["nivel"] < 5:
        return jsonify({"erro": "acesso negado"}), 403

    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor()
    try:
        cur.execute("DELETE FROM incidentes WHERE id = %s", (incidente_id,))
        if cur.rowcount == 0:
            con.rollback()
            return jsonify({"erro": "incidente não encontrado"}), 404
        con.commit()
        return jsonify({"removido": incidente_id}), 200
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    preparar_banco()
    app.run(debug=False, host="127.0.0.1", port=5006)
