"""
Exercício 10 - API corrigida.
Use somente em ambiente local de laboratório.

Credenciais do MySQL vêm de variáveis de ambiente.
"""

import html
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


def db():
    return mysql.connector.connect(**mysql_config())


def preparar_banco():
    con = db()
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            email VARCHAR(150) NOT NULL,
            senha VARCHAR(255) NOT NULL,
            api_key VARCHAR(100) UNIQUE,
            nivel INT NOT NULL
        )
    """)

    cur.execute("SELECT COUNT(*) FROM usuarios")
    if cur.fetchone()[0] == 0:
        # Valores de demonstração são gerados localmente, não são senhas reais.
        import secrets
        dados = [
            (1, "Ana", "ana@example.com", secrets.token_hex(16), secrets.token_hex(16), 5),
            (2, "Bruno", "bruno@example.com", secrets.token_hex(16), secrets.token_hex(16), 2),
            (3, "Caio", "caio@example.com", secrets.token_hex(16), secrets.token_hex(16), 1),
        ]
        cur.executemany(
            "INSERT INTO usuarios (id,nome,email,senha,api_key,nivel) VALUES (%s,%s,%s,%s,%s,%s)",
            dados,
        )
    con.commit()
    cur.close()
    con.close()


@app.after_request
def headers_seguranca(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")

    con = db()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id,nome,email,nivel FROM usuarios WHERE nome LIKE %s",
            (f"%{nome}%",),
        )
        return jsonify(cur.fetchall()), 200
    finally:
        cur.close()
        con.close()


@app.route("/perfil")
def perfil():
    # Escape explícito porque a resposta é HTML montado nesta rota.
    usuario = html.escape(request.args.get("u", ""), quote=True)
    return f"<h1>Bem-vindo, {usuario}</h1>", 200, {"Content-Type": "text/html; charset=utf-8"}


def autenticar_admin():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None, (jsonify({"erro": "autenticação necessária"}), 401)

    con = db()
    cur = con.cursor(dictionary=True)
    try:
        cur.execute(
            "SELECT id,nivel FROM usuarios WHERE api_key = %s",
            (api_key,),
        )
        usuario = cur.fetchone()
    finally:
        cur.close()
        con.close()

    if not usuario:
        return None, (jsonify({"erro": "credencial inválida"}), 401)

    if usuario["nivel"] < 5:
        return None, (jsonify({"erro": "acesso negado"}), 403)

    return usuario, None


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
def remover(uid):
    _, erro = autenticar_admin()
    if erro:
        return erro

    con = db()
    cur = con.cursor()
    try:
        cur.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
        if cur.rowcount == 0:
            con.rollback()
            return jsonify({"erro": "usuário não encontrado"}), 404
        con.commit()
        return jsonify({"removido": uid}), 200
    finally:
        cur.close()
        con.close()


@app.route("/api/relatorio")
def relatorio():
    con = None
    cur = None
    try:
        con = db()
        cur = con.cursor()
        # Consulta inválida propositalmente para demonstrar tratamento seguro de erro.
        cur.execute("SELECT * FROM tabela_inexistente")
        return jsonify(cur.fetchall()), 200
    except Exception:
        return jsonify({"erro": "erro interno"}), 500
    finally:
        if cur:
            cur.close()
        if con:
            con.close()


if __name__ == "__main__":
    preparar_banco()
    app.run(debug=False, host="127.0.0.1", port=5010)
