"""
Exercício 4 - Transação MySQL + trilha de auditoria MongoDB.
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


mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"))
mongo_db = mongo_client[os.getenv("MONGO_DATABASE", "seguranca")]
auditoria = mongo_db["auditoria"]


def registrar_auditoria(quem, alvo, nivel_anterior, nivel_novo, resultado):
    auditoria.insert_one({
        "quem": quem,
        "alvo": alvo,
        "nivel_anterior": nivel_anterior,
        "nivel_novo": nivel_novo,
        "resultado": resultado,
        "timestamp": datetime.utcnow(),
    })


def preparar_banco():
    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS usuarios (id INT PRIMARY KEY, nome VARCHAR(100), email VARCHAR(150), nivel_acesso INT NOT NULL)")
    cur.execute("DELETE FROM usuarios")
    cur.executemany(
        "INSERT INTO usuarios (id,nome,email,nivel_acesso) VALUES (%s,%s,%s,%s)",
        [
            (1, "ana", "ana@x.com", 5),
            (2, "bruno", "bruno@x.com", 2),
            (3, "caio", "caio@x.com", 1),
        ],
    )
    con.commit()
    cur.close()
    con.close()


def alterar_nivel(admin_id, alvo_id, novo_nivel):
    con = mysql.connector.connect(**mysql_config())
    cur = con.cursor(dictionary=True)

    nivel_anterior = None
    resultado = "RECUSADO"

    try:
        con.start_transaction()

        cur.execute("SELECT id, nivel_acesso FROM usuarios WHERE id = %s FOR UPDATE", (admin_id,))
        admin = cur.fetchone()

        cur.execute("SELECT id, nivel_acesso FROM usuarios WHERE id = %s FOR UPDATE", (alvo_id,))
        alvo = cur.fetchone()

        if not admin:
            con.rollback()
            registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
            return "RECUSADO (administrador inexistente)"

        if alvo:
            nivel_anterior = alvo["nivel_acesso"]

        if not alvo:
            con.rollback()
            registrar_auditoria(admin_id, alvo_id, None, novo_nivel, "RECUSADO")
            return "RECUSADO (alvo inexistente)"

        if admin["nivel_acesso"] < 5:
            con.rollback()
            registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, "RECUSADO")
            return "RECUSADO (admin sem privilégio)"

        if admin_id == alvo_id:
            con.rollback()
            registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, "RECUSADO")
            return "RECUSADO (auto-promoção)"

        if not (0 <= int(novo_nivel) <= 10):
            con.rollback()
            registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, "RECUSADO")
            return "RECUSADO (nível inválido)"

        cur.execute(
            "UPDATE usuarios SET nivel_acesso = %s WHERE id = %s",
            (int(novo_nivel), alvo_id),
        )
        con.commit()
        resultado = "OK"
        registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, resultado)
        return "OK"

    except Exception:
        con.rollback()
        registrar_auditoria(admin_id, alvo_id, nivel_anterior, novo_nivel, "RECUSADO")
        return "RECUSADO (erro interno)"
    finally:
        cur.close()
        con.close()


if __name__ == "__main__":
    preparar_banco()
    auditoria.delete_many({})

    testes = [
        (1, 2, 4),
        (2, 3, 5),
        (1, 1, 9),
        (1, 99, 3),
    ]

    for teste in testes:
        print(f"alterar_nivel{teste} -> {alterar_nivel(*teste)}")

    print(f"Trilha de auditoria: {auditoria.count_documents({})} documentos")
    print(f"Recusadas: {auditoria.count_documents({'resultado': 'RECUSADO'})}")
    mongo_client.close()
