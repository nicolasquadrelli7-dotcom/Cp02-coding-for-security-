"""
Exercício 1 - Assistente de decisão de armazenamento.
"""

def recomendar(perfil):
    chaves = {
        "schema_fixo",
        "precisa_acid",
        "escala_horizontal",
        "tolera_atraso_de_consistencia",
        "dado_sensivel",
    }

    faltantes = chaves - perfil.keys()
    if faltantes:
        raise ValueError(f"Chaves ausentes: {sorted(faltantes)}")

    # A decisão do banco considera primeiro a necessidade de ACID/schema.
    # Se isso não for dominante, escala horizontal favorece o modelo documental.
    regras_banco = [
        (
            perfil["precisa_acid"] or perfil["schema_fixo"],
            "MySQL",
            "O erro inaceitável é gravar um estado financeiro ou de autenticação incorreto; por isso o cenário prioriza transações ACID e estrutura controlada.",
        ),
        (
            perfil["escala_horizontal"],
            "MongoDB",
            "O erro inaceitável é parar de aceitar eventos em grande volume; o modelo documental facilita escala horizontal e ingestão.",
        ),
        (
            True,
            "MySQL",
            "Sem necessidade clara de escala horizontal ou flexibilidade, o erro inaceitável é perder consistência estrutural; um esquema relacional facilita esse controle.",
        ),
    ]

    banco, motivo_banco = next(
        (banco, motivo) for condicao, banco, motivo in regras_banco if condicao
    )

    if perfil["tolera_atraso_de_consistencia"]:
        cap = "AP"
        motivo_cap = "É aceitável haver atraso temporário de consistência porque ficar indisponível impediria a coleta ou o uso contínuo dos dados."
    else:
        cap = "CP"
        motivo_cap = "O erro inaceitável é aceitar dados divergentes; por isso a consistência deve ser preservada mesmo com possível perda de disponibilidade."

    # O risco é escolhido pelo tipo de dano causado por uma escolha errada.
    if perfil["precisa_acid"] and perfil["dado_sensivel"]:
        risco = "A07:2025 - Falhas de Autenticação"
    elif perfil["escala_horizontal"] and perfil["tolera_atraso_de_consistencia"]:
        risco = "A09:2025 - Falhas de Registro e Alerta de Segurança"
    elif perfil["dado_sensivel"] and cap == "CP":
        risco = "A08:2025 - Falhas de Integridade de Software e Dados"
    elif perfil["dado_sensivel"]:
        risco = "A07:2025 - Falhas de Autenticação"
    else:
        risco = "A06:2025 - Design Inseguro"

    return {
        "banco": banco,
        "cap": cap,
        "justificativa": f"{motivo_banco} {motivo_cap}",
        "risco_owasp": risco,
    }


if __name__ == "__main__":
    perfis = {
        "credenciais_do_SOC": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
        "telemetria_de_sensores": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": False},
        "trilha_de_auditoria": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
        "carrinho_de_licencas": {"schema_fixo": True, "precisa_acid": True, "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": False},
        "cache_de_sessoes": {"schema_fixo": True, "precisa_acid": False, "escala_horizontal": True, "tolera_atraso_de_consistencia": True, "dado_sensivel": True},
    }

    for nome, perfil in perfis.items():
        print(nome)
        print(recomendar(perfil))
        print("-" * 70)
