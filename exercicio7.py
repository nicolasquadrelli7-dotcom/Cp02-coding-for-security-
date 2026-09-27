"""
Exercício 7 - XSS em atributo HTML.
"""

import html
import os
from flask import Flask, render_template, render_template_string, request, Response
from pymongo import MongoClient

app = Flask(__name__, template_folder="exercicio7_templates")

client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
db = client[os.getenv("MONGO_DATABASE", "seguranca")]
incidentes = db["incidentes_xss"]


@app.after_request
def aplicar_csp(response):
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    return response


@app.route("/icone.png")
def icone():
    # SVG simples servido como imagem para o teste.
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>'
    return Response(svg, mimetype="image/svg+xml")


@app.route("/dashboard")
def dashboard():
    dados = list(incidentes.find({}, {"_id": 0, "titulo": 1, "ativo": 1}))
    return render_template("dashboard.html", incidentes=dados)


@app.route("/dashboard-inseguro")
def dashboard_inseguro():
    dados = list(incidentes.find({}, {"_id": 0, "titulo": 1, "ativo": 1}))
    linhas = []
    for item in dados:
        titulo = item.get("titulo", "")
        ativo = item.get("ativo", "")
        linhas.append(
            f'<tr><td>{titulo}</td><td><img src="/icone.png" alt="{ativo}"></td></tr>'
        )
    return render_template_string(
        "<h1>COMPARAÇÃO - INSEGURO</h1><table><tr><th>Título</th><th>Ativo</th></tr>"
        + "".join(linhas)
        + "</table>"
    )


def preparar_dados():
    incidentes.delete_many({})
    p1 = "<script>alert('xss1')</script>"
    p2 = 'x" onerror="alert(\'xss2\')'
    incidentes.insert_many([
        {"titulo": p1, "ativo": "SRV-WEB01"},
        {"titulo": "Incidente 2", "ativo": p2},
    ])


if __name__ == "__main__":
    preparar_dados()
    app.run(debug=False, host="127.0.0.1", port=5007)
