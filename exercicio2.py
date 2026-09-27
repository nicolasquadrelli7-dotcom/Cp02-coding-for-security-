"""
Exercício 2 - Migração relacional -> documentos.
"""

import os
from datetime import datetime
import mysql.connector
from pymongo import MongoClient


def mysql_config():
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "seguranca"),
    }


def main():
    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)

    cur.execute("CREATE DATABASE IF NOT EXISTS seguranca")
    cur.execute("USE seguranca")

    cur.execute("DROP TABLE IF EXISTS alertas")
    cur.execute("DROP TABLE IF EXISTS ativos")

    cur.execute("""
        CREATE TABLE ativos (
            id INT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            ip VARCHAR(45) NOT NULL UNIQUE,
            criticidade ENUM('baixa','media','alta') NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE alertas (
            id INT PRIMARY KEY,
            ativo_id INT NOT NULL,
            tipo VARCHAR(50) NOT NULL,
            severidade VARCHAR(20) NOT NULL,
            criado_em DATETIME NOT NULL,
            FOREIGN KEY (ativo_id) REFERENCES ativos(id)
        )
    """)

    ativos = [
        (1, "SRV-WEB01", "192.168.1.10", "alta"),
        (2, "PC-RH03", "192.168.1.45", "baixa"),
    ]
    agora = datetime.now()
    alertas = [
        (1, 1, "BRUTE_FORCE", "critica", agora),
        (2, 1, "PORT_SCAN", "alta", agora),
        (3, 2, "XSS", "media", agora),
    ]

    cur.executemany(
        "INSERT INTO ativos (id,nome,ip,criticidade) VALUES (%s,%s,%s,%s)",
        ativos,
    )
    cur.executemany(
        "INSERT INTO alertas (id,ativo_id,tipo,severidade,criado_em) VALUES (%s,%s,%s,%s,%s)",
        alertas,
    )
    con.commit()

    # JOIN parametrizado: o valor do ativo é passado como parâmetro.
    filtro_ativo = 0
    cur.execute("""
        SELECT a.id AS alerta_id, a.tipo, a.severidade, a.criado_em,
               at.nome, at.ip, at.criticidade
        FROM alertas a
        JOIN ativos at ON at.id = a.ativo_id
        WHERE at.id >= %s
        ORDER BY a.id
    """, (filtro_ativo,))
    linhas = cur.fetchall()

    mongo = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
    db = mongo[os.getenv("MONGO_DATABASE", "seguranca")]
    colecao = db["alertas"]
    colecao.delete_many({})

    documentos = [
        {
            "tipo": linha["tipo"],
            "severidade": linha["severidade"],
            "criado_em": linha["criado_em"],
            "ativo": {
                "nome": linha["nome"],
                "ip": linha["ip"],
                "criticidade": linha["criticidade"],
            },
        }
        for linha in linhas
    ]

    if documentos:
        colecao.insert_many(documentos)

    cur.execute("SELECT COUNT(*) AS total FROM alertas")
    total_mysql = cur.fetchone()["total"]
    total_mongo = colecao.count_documents({})

    print(f"MySQL: {total_mysql} alertas | MongoDB: {total_mongo} documentos -> "
          f"{'MIGRAÇÃO ÍNTEGRA' if total_mysql == total_mongo else 'MIGRAÇÃO INCOMPLETA'}")

    altas = list(colecao.find({"ativo.criticidade": "alta"}))
    print(f'Consulta sem JOIN: db.alertas.find({{"ativo.criticidade":"alta"}}) -> {len(altas)} documentos')

    print("Ganho: a leitura do alerta já traz os dados do ativo, evitando JOIN em consultas frequentes.")
    print("Perda: há duplicação; se o ativo mudar, documentos relacionados precisam ser atualizados.")

    cur.close()
    con.close()
    mongo.close()


if __name__ == "__main__":
    main()
